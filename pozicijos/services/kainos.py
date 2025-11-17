# pozicijos/services/kainos.py
from __future__ import annotations
from dataclasses import dataclass
from decimal import Decimal
from typing import Optional, Iterable
from datetime import date, MAXYEAR

from django.db import transaction
from django.db.models import Q
from django.utils import timezone

from ..models import KainosEilute, Pozicija


@dataclass
class KainosCreateData:
    pozicija: Pozicija
    kaina: Decimal
    matas: str = "vnt."
    yra_fiksuota: bool = False
    fiksuotas_kiekis: Optional[int] = None
    kiekis_nuo: Optional[int] = None
    kiekis_iki: Optional[int] = None
    galioja_nuo: Optional[date] = None
    galioja_iki: Optional[date] = None
    busena: str = "aktuali"
    prioritetas: int = 100
    pastaba: Optional[str] = None


def _now_date() -> date:
    return timezone.localdate()


def _end_of_time() -> date:
    return date(MAXYEAR, 12, 31)


def _overlap(a_from: Optional[date], a_to: Optional[date],
             b_from: Optional[date], b_to: Optional[date]) -> bool:
    """Ar laiko intervalai kertasi? None = atvira riba."""
    a_from = a_from or _now_date()
    b_from = b_from or _now_date()
    a_to = a_to or _end_of_time()
    b_to = b_to or _end_of_time()
    return not (a_to < b_from or b_to < a_from)


def _qty_overlap(nuo1: Optional[int], iki1: Optional[int],
                 nuo2: Optional[int], iki2: Optional[int]) -> bool:
    """Ar kiekio intervalai kertasi? None = atvira riba."""
    nuo1 = 0 if nuo1 is None else nuo1
    nuo2 = 0 if nuo2 is None else nuo2
    iki1 = float("inf") if iki1 is None else iki1
    iki2 = float("inf") if iki2 is None else iki2
    return not (iki1 < nuo2 or iki2 < nuo1)


def find_for_qty(pozicija: Pozicija, qty: int, matas: str = "vnt.", as_of: Optional[date] = None) -> Optional[KainosEilute]:
    """Randa vieną galiojančią „aktualią“ kainą nurodytam kiekiui."""
    as_of = as_of or _now_date()
    qs = KainosEilute.objects.filter(
        pozicija=pozicija, matas=matas, busena="aktuali",
    ).filter(
        Q(galioja_nuo__isnull=True) | Q(galioja_nuo__lte=as_of)
    ).filter(
        Q(galioja_iki__isnull=True) | Q(galioja_iki__gte=as_of)
    )

    # 1) fiksuota
    fx = qs.filter(yra_fiksuota=True, fiksuotas_kiekis=qty).order_by("prioritetas", "-created").first()
    if fx:
        return fx
    # 2) intervalas
    iv = qs.filter(yra_fiksuota=False) \
           .filter(Q(kiekis_nuo__isnull=True) | Q(kiekis_nuo__lte=qty)) \
           .filter(Q(kiekis_iki__isnull=True) | Q(kiekis_iki__gte=qty)) \
           .order_by("prioritetas", "-created").first()
    return iv


@transaction.atomic

def set_aktuali(k: KainosEilute) -> KainosEilute:
    """
    Pažymi eilutę „aktuali“ ir 'pasendina' konfliktines to paties tipo/mato eilutes,
    persidengiančias pagal laiką ir kiekį.
    """
    conflicts = KainosEilute.objects.filter(
        pozicija=k.pozicija, matas=k.matas, busena="aktuali"
    ).exclude(pk=k.pk)

    if k.yra_fiksuota:
        # konfliktas tik su tuo pačiu fiksuotu kiekiu
        conflicts = conflicts.filter(yra_fiksuota=True, fiksuotas_kiekis=k.fiksuotas_kiekis)
    else:
        # grubus filtras: tik intervalinės
        conflicts = conflicts.filter(yra_fiksuota=False)

    # tiksliai patikrinam persidengimus
    for c in conflicts:
        overlaps_qty = (
            (k.yra_fiksuota and c.yra_fiksuota and c.fiksuotas_kiekis == k.fiksuotas_kiekis) or
            (not k.yra_fiksuota and not c.yra_fiksuota and _qty_overlap(k.kiekis_nuo, k.kiekis_iki, c.kiekis_nuo, c.kiekis_iki))
        )
        overlaps_time = _overlap(k.galioja_nuo, k.galioja_iki, c.galioja_nuo, c.galioja_iki)
        if overlaps_qty and overlaps_time:
            c.busena = "sena"
            c.save(update_fields=["busena", "updated"])

    if k.busena != "aktuali":
        k.busena = "aktuali"
        k.save(update_fields=["busena", "updated"])
    return k


@transaction.atomic
def create_or_update_kaina(data: KainosCreateData) -> KainosEilute:
    """Sukuria kainą su validacija ir, jei reikia, pažymi kaip aktualią."""
    k = KainosEilute(
        pozicija=data.pozicija,
        kaina=data.kaina,
        matas=data.matas,
        yra_fiksuota=data.yra_fiksuota,
        fiksuotas_kiekis=data.fiksuotas_kiekis,
        kiekis_nuo=data.kiekis_nuo,
        kiekis_iki=data.kiekis_iki,
        galioja_nuo=data.galioja_nuo or _now_date(),
        galioja_iki=data.galioja_iki,
        busena=data.busena,
        prioritetas=data.prioritetas,
        pastaba=data.pastaba,
    )
    k.full_clean()
    k.save()
    if data.busena == "aktuali":
        set_aktuali(k)
    return k


def all_active_matrix(pozicija: Pozicija, matas: str = "vnt.", as_of: Optional[date] = None) -> Iterable[KainosEilute]:
    """Visos galiojančios „aktualios“ eilutės lentelei/matricai."""
    as_of = as_of or _now_date()
    return KainosEilute.objects.filter(
        pozicija=pozicija, matas=matas, busena="aktuali"
    ).filter(
        Q(galioja_nuo__isnull=True) | Q(galioja_nuo__lte=as_of)
    ).filter(
        Q(galioja_iki__isnull=True) | Q(galioja_iki__gte=as_of)
    ).order_by("yra_fiksuota", "kiekis_nuo", "fiksuotas_kiekis", "prioritetas", "-created")
