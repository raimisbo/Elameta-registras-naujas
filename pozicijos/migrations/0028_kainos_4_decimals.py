from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("pozicijos", "0027_maskavimoeilute"),
    ]

    operations = [
        migrations.AlterField(
            model_name="kainoseilute",
            name="kaina",
            field=models.DecimalField(
                verbose_name="Kaina",
                max_digits=12,
                decimal_places=4,
                null=True,
                blank=True,
            ),
        ),
        migrations.AlterField(
            model_name="pozicija",
            name="kaina_eur",
            field=models.DecimalField(
                verbose_name="Kaina (EUR)",
                max_digits=12,
                decimal_places=4,
                null=True,
                blank=True,
            ),
        ),
    ]
