from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("pozicijos", "0022_alter_pozicija_atlikimo_terminas_data"),
    ]

    operations = [
        migrations.AddField(
            model_name="pozicija",
            name="paslaugu_pastabos",
            field=models.TextField(blank=True, null=True, verbose_name="Paslaugų pastabos"),
        ),
    ]
