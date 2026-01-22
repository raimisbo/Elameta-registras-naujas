# pozicijos/management/commands/backfill_kainos.py
from django.core.management.base import BaseCommand

from pozicijos.models import Pozicija, KainosEilute


class Command(BaseCommand):
    help = (
        "Sukuria bazines KainosEilute eilutes iš esamo Pozicija.kaina_eur, "
        "jei dar nėra nė vienos 'aktuali' kainos šiai pozicijai."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Nieko neišsaugoti, tik parodyti, kas būtų padaryta.",
        )

    def handle(self, *args, **options):
        dry_run = options["dry_run"]

        # Imame tik tas pozicijas, kuriose yra įvesta kaina_eur
        pozicijos_qs = Pozicija.objects.filter(kaina_eur__isnull=False)
        total = pozicijos_qs.count()

        created = 0
        skipped_existing_aktuali = 0

        self.stdout.write(
            self.style.MIGRATE_HEADING(
                f"Pradedamas backfill: pozicijų su kaina_eur = {total}, dry_run={dry_run}"
            )
        )

        for poz in pozicijos_qs.iterator():
            kaina = poz.kaina_eur

            # Jei jau yra bent viena 'aktuali' kaina šiai pozicijai – nieko nebedarom
            if poz.kainos_eilutes.filter(busena="aktuali").exists():
                skipped_existing_aktuali += 1
                continue

            msg = (
                f"Pozicija id={poz.id}, kodas={poz.poz_kodas!r}: "
                f"sukuriama KainosEilute su kaina={kaina} EUR, matas='vnt.'"
            )

            if dry_run:
                self.stdout.write("[DRY-RUN] " + msg)
            else:
                KainosEilute.objects.create(
                    pozicija=poz,
                    kaina=kaina,
                    matas="vnt.",
                    yra_fiksuota=False,
                    kiekis_nuo=None,
                    kiekis_iki=None,
                    galioja_nuo=None,
                    galioja_iki=None,
                    busena="aktuali",
                    prioritetas=100,
                    pastaba="Sugeneruota iš pozicija.kaina_eur backfill metu",
                )
                self.stdout.write(self.style.SUCCESS(msg))

            created += 1

        self.stdout.write("")
        self.stdout.write(self.style.MIGRATE_LABEL("Santrauka:"))
        self.stdout.write(self.style.NOTICE(f"  Pozicijų su kaina_eur: {total}"))
        self.stdout.write(
            self.style.NOTICE(
                f"  Sukurta naujų KainosEilute: {created} (dry_run={dry_run})"
            )
        )
        self.stdout.write(
            self.style.NOTICE(
                f"  Praleista (jau turi 'aktuali' kainą): {skipped_existing_aktuali}"
            )
        )

        if dry_run:
            self.stdout.write(
                self.style.WARNING(
                    "Dry-run režimas: duomenys NEBUVO išsaugoti. "
                    "Jei rezultatai tinka, paleisk be --dry-run."
                )
            )
