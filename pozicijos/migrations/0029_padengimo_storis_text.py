from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("pozicijos", "0028_kainos_4_decimals"),
    ]

    operations = [
        migrations.AlterField(
            model_name="pozicija",
            name="padengimo_storis_um",
            field=models.CharField(
                verbose_name="Padengimo storis (µm)",
                max_length=32,
                blank=True,
                default="",
            ),
        ),
    ]
