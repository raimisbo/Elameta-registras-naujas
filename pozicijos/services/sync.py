# pozicijos/services/sync.py
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from ..models import KainosEilute, Pozicija


@dataclass(frozen=True)
class KainaEurSyncResult:
    old: Optional[object]
    new: Optional[object]
    changed: bool


def sync_pozicija_kaina_eur(pozicija: Pozicija, *, save: bool = True) -> KainaEurSyncResult:
    """
    Vienintelis tiesos šaltinis Pozicija.kaina_eur.

    Sutarta taisyklė:
      - Pozicija.kaina_eur = pirmos KainosEilute eilutės kaina,
        kai KainosEilute.busena == 'aktuali', rikiuojant:
          prioritetas ASC, created DESC.
      - Jei aktualių eilučių nėra (arba jų kaina NULL) -> None.

    Pastaba: ši funkcija turi būti kviečiama po bet kokio kainų įrašo
    sukūrimo/keitimo/trynimo/„set aktuali“ veiksmo.
    """
    old = pozicija.kaina_eur

    akt = (
        KainosEilute.objects
        .filter(pozicija=pozicija, busena="aktuali")
        .order_by("prioritetas", "-created")
        .first()
    )
    new = getattr(akt, "kaina", None) if akt else None

    changed = (old != new)

    if save and changed:
        pozicija.kaina_eur = new
        pozicija.save(update_fields=["kaina_eur", "updated"])

    return KainaEurSyncResult(old=old, new=new, changed=changed)
