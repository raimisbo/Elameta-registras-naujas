from django.core.management.base import BaseCommand
from django.apps import apps
from pozicijos.schemas.columns import COLUMNS

class Command(BaseCommand):
    help = "Tikrina, ar columns.py raktai sutampa su Pozicija modelio laukais (virtual ignoruojami)."

    def handle(self, *args, **options):
        Pozicija = apps.get_model("pozicijos", "Pozicija")
        model_fields = {f.name for f in Pozicija._meta.get_fields() if hasattr(f, "attname")}
        col_keys = {c["key"] for c in COLUMNS if c.get("type") != "virtual"}

        missing_in_model = sorted(col_keys - model_fields)
        extra_in_model = sorted((model_fields - col_keys) - {"id", "created", "updated"})

        if not missing_in_model and not extra_in_model:
            self.stdout.write(self.style.SUCCESS("Viskas gerai: columns.py atitinka Pozicija modelį."))
            return

        if missing_in_model:
            self.stdout.write(self.style.ERROR("Trūksta modelyje (columns.py → modelio laukų nėra):"))
            for k in missing_in_model:
                self.stdout.write(f"  - {k}")

        if extra_in_model:
            self.stdout.write(self.style.WARNING("Papildomi laukai modelyje (nėra columns.py):"))
            for k in extra_in_model:
                self.stdout.write(f"  - {k}")
