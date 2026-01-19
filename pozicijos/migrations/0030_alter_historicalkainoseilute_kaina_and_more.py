from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("pozicijos", "0029_padengimo_storis_text"),
    ]

    operations = [
        migrations.AlterField(
            model_name="historicalkainoseilute",
            name="kaina",
            field=models.DecimalField(
                blank=True,
                decimal_places=4,
                max_digits=12,
                null=True,
                verbose_name="Kaina",
            ),
        ),
        migrations.AlterField(
            model_name="historicalpozicija",
            name="kaina_eur",
            field=models.DecimalField(
                blank=True,
                decimal_places=4,
                max_digits=12,
                null=True,
                verbose_name="Kaina (EUR)",
            ),
        ),
        migrations.AlterField(
            model_name="historicalpozicija",
            name="padengimo_storis_um",
            field=models.CharField(
                blank=True,
                default="",
                max_length=32,
                verbose_name="Padengimo storis (µm)",
            ),
        ),
    ]
