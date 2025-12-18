# pozicijos/migrations/00XX_maskavimas_nera.py
from django.db import migrations


def normalize_maskavimas(apps, schema_editor):
    Pozicija = apps.get_model("pozicijos", "Pozicija")

    # viską, kas nėra "yra", laikom "nera"
    Pozicija.objects.filter(maskavimo_tipas__isnull=True).update(maskavimo_tipas="nera")
    Pozicija.objects.filter(maskavimo_tipas="").update(maskavimo_tipas="nera")
    Pozicija.objects.filter(maskavimo_tipas="ners").update(maskavimo_tipas="nera")
    Pozicija.objects.filter(maskavimo_tipas="iprastas").update(maskavimo_tipas="yra")
    Pozicija.objects.filter(maskavimo_tipas="specialus").update(maskavimo_tipas="yra")

    # jei tipas nera – aprašymas turi būti tuščias
    Pozicija.objects.filter(maskavimo_tipas="nera").update(maskavimas="")


class Migration(migrations.Migration):

    dependencies = [
        ("pozicijos", "0019_alter_pozicija_maskavimo_tipas"),
    ]

    operations = [
        migrations.RunPython(normalize_maskavimas, migrations.RunPython.noop),
    ]
