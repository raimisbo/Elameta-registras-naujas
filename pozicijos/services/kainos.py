# pozicijos/services/kainos.py
from __future__ import annotations

from datetime import date, timedelta
from typing import Optional

from django.db import transaction
from django.db.models import Q, QuerySet

from ..models import KainosEilute, Pozicija


def _group_filter_for(row: KainosEilute) -> Q:
    """
    Apibrėžia „grupę“, kurioje gali būti tik viena AKTUALI kaina.

    Grupė apibrėžiama:
      - ta pati pozicija
      - tas pats matas
      - tas pats tipas (fiksuota / intervalinė)
      - fiksuotai: tas pats fiksuotas_kiekis
      - intervalinei: tas pats (kiekis_nuo, kiekis_iki)
    """
    q = Q(pozicija=row.pozicija, matas=row.matas)

    if row.yra_fiksuota:
        q &= Q(yra_fiksuota=True, fiksuotas_kiekis=row.fiksuotas_kiekis)
    else:
        q &= Q(
            yra_fiksuota=False,
            kiekis_nuo=row.kiekis_nuo,
            kiekis_iki=row.kiekis_iki,
        )

    return q


@transaction.atomic
def set_aktuali(row: KainosEilute, save: bool = True) -> KainosEilute:
    """
    Pažymi eilutę kaip AKTUALI ir pasirūpina, kad toje grupėje liktų tik viena.

    - Jei save=True, eilutei nustato busena='aktuali' ir ją išsaugo.
    - Visoms kitoms tos grupės AKTUALI eilutėms:
        * busena -> 'sena'
        * jei įmanoma, patrumpina jų galiojimą (galioja_iki = nauja.galioja_nuo - 1d)
    - Papildomai:
        * atnaujina pozicija.kaina_eur => susiejimas su sąrašo „Kaina“ stulpeliu.
    """
    if save:
        row.busena = "aktuali"
        row.save()

    # Randam kitas AKTUALIAS konfliktuojančias eilutes
    group_q = _group_filter_for(row)
    others = (
        KainosEilute.objects
        .filter(group_q, busena="aktuali")
        .exclude(pk=row.pk)
    )

    for old in others:
        old.busena = "sena"

        # Variant B: jeigu nauja turi galioja_nuo – patrumpinam senos galioja_iki
        if row.galioja_nuo:
            # Jei sena neturi pabaigos arba baigiasi vėliau nei naujos pradžia
            if old.galioja_iki is None or old.galioja_iki >= row.galioja_nuo:
                candidate_end = row.galioja_nuo - timedelta(days=1)
                # neleidžiam, kad pabaiga būtų prieš pradžią (jei sena turi nuo)
                if not old.galioja_nuo or candidate_end >= old.galioja_nuo:
                    old.galioja_iki = candidate_end

        old.save()

    # --- SUSIEJIMAS SU SĄRAŠO KAINOS STULPELIU ---
    # Čia darom „santrauką“: pozicija.kaina_eur = naujos AKTUALIOS eilutės suma.
    # Sąrašo „Kaina“ stulpelis, jei naudoja pozicija.kaina_eur, visada rodys naujausią aktualią kainą.
    poz = row.pozicija
    if poz is not None:
        poz.kaina_eur = row.kaina
        # jei nori, atnaujinam ir updated lauką; jis pas tave yra modelyje
        poz.save(update_fields=["kaina_eur", "updated"])

    return row


def aktualios_kainos(
    pozicija: Pozicija,
    matas: Optional[str] = None,
    as_of: Optional[date] = None,
) -> QuerySet[KainosEilute]:
    """
    Grąžina AKTUALIAS kainas pozicijai (pagal datą ir, jei nurodytas, matą).
    Naudojama tiek UI, tiek logikai.
    """
    as_of = as_of or date.today()

    qs = pozicija.kainu_eilutes.filter(
        busena="aktuali",
    ).filter(
        Q(galioja_nuo__isnull=True) | Q(galioja_nuo__lte=as_of)
    ).filter(
        Q(galioja_iki__isnull=True) | Q(galioja_iki__gte=as_of)
    )

    if matas:
        qs = qs.filter(matas=matas)

    return qs.order_by(
        "matas",
        "yra_fiksuota",
        "kiekis_nuo",
        "fiksuotas_kiekis",
        "prioritetas",
        "-created",
    )


def find_for_qty(
    pozicija: Pozicija,
    qty: int,
    matas: str = "vnt.",
    as_of: Optional[date] = None,
) -> Optional[KainosEilute]:
    """
    Parenka tinkamiausią AKTUALIĄ kainą pagal kiekį.

    1) Pirma bando rasti fiksuotą (yra_fiksuota=True, fiksuotas_kiekis=qty)
    2) Jei neranda – ieško intervalo:
         kiekis_nuo <= qty <= kiekis_iki
         (arba atitinkamai su None kraštais)
    3) Jei keli kandidatai – laimi:
         - mažesnis prioritetas
         - naujesnis created
    """
    as_of = as_of or date.today()
    qs = aktualios_kainos(pozicija, matas=matas, as_of=as_of)

    # 1) Fiksuotos
    fx = (
        qs.filter(yra_fiksuota=True, fiksuotas_kiekis=qty)
        .order_by("prioritetas", "-created")
        .first()
    )
    if fx:
        return fx

    # 2) Intervalinės
    iv = (
        qs.filter(yra_fiksuota=False)
        .filter(Q(kiekis_nuo__isnull=True) | Q(kiekis_nuo__lte=qty))
        .filter(Q(kiekis_iki__isnull=True) | Q(kiekis_iki__gte=qty))
        .order_by("prioritetas", "-created")
        .first()
    )
    return iv
