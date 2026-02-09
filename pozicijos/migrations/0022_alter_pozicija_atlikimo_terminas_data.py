from django.db import migrations


class Migration(migrations.Migration):
    """
    Placeholder migration.

    0023 turi dependency į 0022, bet 0022 failas buvo pradingęs (pvz. po git reset).
    Ši migracija neturi operations – ji tik atstato migracijų grandinę.
    """

    dependencies = [
        ("pozicijos", "0021_atlikimo_terminas_darbo_dienos"),
    ]

    operations = []
