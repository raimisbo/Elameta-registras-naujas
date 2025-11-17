# pozicijos/management/commands/regen_previews.py
from django.core.management.base import BaseCommand
from pozicijos.models import PozicijosBrezinys
from pozicijos.services.previews import regenerate_missing_preview

class Command(BaseCommand):
    help = "Sugeneruoja trūkstamas peržiūras (PNG) PDF/TIFF/kitų brėžinių failams."

    def add_arguments(self, parser):
        parser.add_argument("--all", action="store_true", help="Regeneruoti visiems (net jei jau yra)")

    def handle(self, *args, **options):
        total = 0
        ok = 0
        for b in PozicijosBrezinys.objects.all().iterator():
            total += 1
            if options.get("all"):
                # jei --all, ignoruojam ar yra, tiesiog bandome generuoti
                res = regenerate_missing_preview(b)  # šita gerbia „yra/nera“ – tada „force“ nebus
                if not res.ok:
                    # jei nori VISIŠKAI priverstinai, galima perrašyti _save_preview iš delete(), bet nebūtina
                    self.stdout.write(self.style.WARNING(f"[SKIP] {b.id} {b.failas.name}: {res.message}"))
                else:
                    ok += 1
                    self.stdout.write(self.style.SUCCESS(f"[OK] {b.id} {b.failas.name}"))
            else:
                # tik trūkstami
                res = regenerate_missing_preview(b)
                if not res.ok:
                    self.stdout.write(self.style.WARNING(f"[MISS] {b.id} {b.failas.name}: {res.message}"))
                else:
                    ok += 1
                    self.stdout.write(self.style.SUCCESS(f"[OK] {b.id} {b.failas.name}"))

        self.stdout.write(self.style.SUCCESS(f"Baigta. Apdorota: {total}, sėkmingai: {ok}"))
