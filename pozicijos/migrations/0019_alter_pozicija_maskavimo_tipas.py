from django.db import migrations


class Migration(migrations.Migration):
    """
    Placeholder migration.

    Projekto istorijoje egzistavo 0019_alter_pozicija_maskavimo_tipas, o 0020_maskavimas_nera
    turi dependency į jį. Failas buvo pradingęs (pvz. po git reset / cherry-pick), todėl
    Django negalėjo sudaryti migracijų grafiko.

    Ši migracija sąmoningai neturi operations – ji tik atstato migracijų grandinę.
    """

    dependencies = [
        ("pozicijos", "0001_initial"),
    ]

    operations = []
