# pozicijos/signals.py
from __future__ import annotations

import logging
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver

from .models import PozicijosBrezinys
from .services.previews import generate_preview_for_instance

logger = logging.getLogger(__name__)


@receiver(post_save, sender=PozicijosBrezinys)
def auto_preview_on_create(sender, instance: PozicijosBrezinys, created: bool, **kwargs):
    """
    Kiekvieno naujo brėžinio įkėlimo metu bandome sugeneruoti PNG peržiūrą.
    PDF/TIFF → PNG (per PyMuPDF/Pillow), kiti vaizdai ↓sumenkinami.
    Jei nepavyksta – neužkliūna request'o (tiesiog suloginam).
    """
    if not created:
        return

    try:
        res = generate_preview_for_instance(instance)
        if not res.ok:
            logger.info("Preview not generated for id=%s: %s", instance.pk, res.message)
        else:
            logger.debug("Preview saved for id=%s at %s", instance.pk, res.saved_path)
    except Exception as e:
        # niekada nemetam iš signalo – tik log'as
        logger.exception("Preview generation failed for id=%s: %s", instance.pk, e)


@receiver(post_delete, sender=PozicijosBrezinys)
def cleanup_files_on_delete(sender, instance: PozicijosBrezinys, **kwargs):
    """
    Apsauginis valymas, kai įrašas ištrinamas ne per instance.delete(),
    o masiškai (QuerySet.delete) ar per admin bulk action:
    - pašalinam originalų failą, jei dar egzistuoja
    - pašalinam sugeneruotą preview PNG
    """
    storage = instance.failas.storage
    orig = getattr(instance.failas, "name", None)

    # Preview kelias gaunamas iš helperio, net jei originalo jau nėra
    try:
        prev_rel = instance._preview_relpath()
    except Exception:
        prev_rel = None

    # trinam tyliai – jokių išimčių nekeliam
    try:
        if orig and storage.exists(orig):
            storage.delete(orig)
    except Exception:
        logger.debug("Couldn't delete original file for id=%s (maybe already gone).", instance.pk)

    try:
        if prev_rel and storage.exists(prev_rel):
            storage.delete(prev_rel)
    except Exception:
        logger.debug("Couldn't delete preview for id=%s (maybe already gone).", instance.pk)
