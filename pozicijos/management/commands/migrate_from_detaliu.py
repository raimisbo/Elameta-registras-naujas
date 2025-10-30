from django.core.management.base import BaseCommand
from django.apps import apps
from pozicijos.models import Pozicija

class Command(BaseCommand):
    help = "Perkelia pagrindinius laukus iš detaliu_registras į pozicijos.Pozicija"

    def add_arguments(self, parser):
        parser.add_argument("--dry-run", action="store_true", help="Nerašyti į DB, tik parodyti kiek būtų sukurta.")

    def handle(self, *args, **opts):
        # Pritaikyk pavadinimus pagal savo seną modelį:
        # tarkim, buvo modelis Uzklausa su laukais: kodas, pavadinimas, klientas, projektas, spalva, kaina
        Uzklausa = apps.get_model("detaliu_registras", "Uzklausa")
        qs = Uzklausa.objects.all()
        created = skipped = 0

        for u in qs.iterator():
            key = getattr(u, "kodas", None) or getattr(u, "id", None)
            name = getattr(u, "pavadinimas", None)
            klientas = getattr(u, "klientas", None)
            projektas = getattr(u, "projektas", None)
            spalva = getattr(u, "spalva", None)
            kaina = getattr(u, "kaina", None)

            if not key and not name:
                skipped += 1
                continue

            defaults = dict(
                poz_pavad=name or "",
                klientas=klientas or "",
                projektas=projektas or "",
                spalva=spalva or "",
                kaina_eur=kaina,
            )
            if opts["dry_run"]:
                created += 1
            else:
                _, was_created = Pozicija.objects.get_or_create(poz_kodas=str(key), defaults=defaults)
                if was_created:
                    created += 1

        self.stdout.write(self.style.SUCCESS(
            f"{'Būtų sukurta' if opts['dry_run'] else 'Sukurta'}: {created}, praleista: {skipped}"
        ))
