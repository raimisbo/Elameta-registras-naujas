from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("pozicijos", "0040_metalo_storis"),
    ]

    operations = [
        migrations.CreateModel(
            name="MetaloStorisEilute",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("storis_mm", models.DecimalField(blank=True, decimal_places=2, max_digits=10, null=True, verbose_name="Metalo storis (mm)")),
                ("created", models.DateTimeField(auto_now_add=True, verbose_name="Sukurta")),
                ("updated", models.DateTimeField(auto_now=True, verbose_name="Atnaujinta")),
                (
                    "pozicija",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="metalo_storio_eilutes",
                        to="pozicijos.pozicija",
                        verbose_name="Pozicija",
                    ),
                ),
            ],
            options={
                "verbose_name": "Metalo storio eilutė",
                "verbose_name_plural": "Metalo storio eilutės",
                "ordering": ["id"],
            },
        ),
    ]
