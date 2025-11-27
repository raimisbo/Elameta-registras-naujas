# pozicijos/signals.py
from __future__ import annotations

import logging

from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver

from .models import PozicijosBrezinys
from .thumbnails import generate_brezinys_thumbnail

logger = logging.getLogger(__name__)


@receiver(post_save, sender=PozicijosBrezinys)
def auto_preview_on_create(sender, instance: PozicijosBrezinys, created: bool, **kwargs):
    """
    Kiekvieno naujo brėžinio įkėlimo metu bandome sugeneruoti PNG miniatiūrą.
    JPG/PNG/TIFF → sumažintas vaizdas, PDF → 1 puslapio PNG (jei yra pdf2image),
    STEP/STP → placeholder "3D". Jei nepavyksta – request'o negadinam, tik log.
    """
    if not created or not instance.failas:
        return

    try:
        created_thumb = generate_brezinys_thumbnail(instance)
        if created_thumb:
            logger.debug("Preview generated for brezinys id=%s", instance.pk)
        else:
            logger.info("Preview not generated for brezinys id=%s (maybe no handler).", instance.pk)
    except Exception as e:
        # niekada nemetam iš signalo – tik log'as
        logger.exception("Preview generation failed for brezinys id=%s: %s", instance.pk, e)


@receiver(post_delete, sender=PozicijosBrezinys)
def cleanup_files_on_delete(sender, instance: PozicijosBrezinys, **kwargs):
    """
    Apsauginis valymas, kai įrašas ištrinamas ne per instance.delete(),
    o masiškai (QuerySet.delete) ar per admin bulk action:

    - pašalinam originalų failą, jei dar egzistuoja
    - pašalinam ImageField preview (jei yra)
    - pašalinam senus preview PNG failus pagal _preview_relpath / _legacy_preview_relpath
    """
    storage = instance.failas.storage
    paths_to_delete: list[str] = []

    # originalus failas
    orig = getattr(instance.failas, "name", None)
    if orig:
        paths_to_delete.append(orig)

    # ImageField preview failas (jei yra)
    preview_name = instance.preview.name if getattr(instance, "preview", None) else None
    if preview_name:
        paths_to_delete.append(preview_name)

    # naujas ir legacy preview keliai (jei helperiai veikia)
    try:
        rel_new = instance._preview_relpath()
        if rel_new:
            paths_to_delete.append(rel_new)
    except Exception:
        rel_new = None

    try:
        rel_old = instance._legacy_preview_relpath()
        if rel_old:
            paths_to_delete.append(rel_old)
    except Exception:
        rel_old = None

    # trinam tyliai – jokių išimčių nekeliam
    for path in paths_to_delete:
        try:
            if path and storage.exists(path):
                storage.delete(path)
        except Exception:
            logger.debug(
                "Couldn't delete file '%s' for brezinys id=%s (maybe already gone).",
                path,
                instance.pk,
            )
