from django.core.management.base import BaseCommand
from pozicijos.models import Pozicija

SAMPLE = [
    dict(
        klientas="UAB Klientas A", projektas="Projektas A",
        poz_kodas="DA-0001", poz_pavad="Laikiklis A",
        metalas="Plienas", plotas="1.25 m2", svoris="3.4 kg",
        kabinimo_budas="Kablys", kabinimas_reme="3-4-2",
        detaliu_kiekis_reme=24, faktinis_kiekis_reme=22,
        paruosimas="Smėliavimas SA2.5", padengimas="KTL + miltelinis",
        padengimo_standartas="ISO 12944 C3", spalva="RAL9005",
        maskavimas="Sriegiai užmaskuoti",
        testai_kokybe="Adhezijos testas OK", pakavimas="Dėžės",
        instrukcija="Sutvirtinti kampuose", pakavimo_dienos_norma=120,
        pak_po_ktl=60, pak_po_milt=40, kaina_eur=12.50,
        pastabos="Pirmas bandymas"
    ),
    dict(
        klientas="UAB Klientas B", projektas="Projektas B",
        poz_kodas="DA-0002", poz_pavad="Dangtelis B",
        metalas="Aliuminis", plotas="0.95 m2", svoris="2.1 kg",
        kabinimo_budas="Vielutė", kabinimas_reme="2-3-2",
        detaliu_kiekis_reme=18, faktinis_kiekis_reme=18,
        paruosimas="Fosfatavimas", padengimas="Miltelinis",
        padengimo_standartas="Qualicoat", spalva="RAL9010",
        maskavimas="",
        testai_kokybe="Druskos rūko testas 240h", pakavimas="Euro padėklas",
        instrukcija="", pakavimo_dienos_norma=90,
        pak_po_ktl=0, pak_po_milt=90, kaina_eur=9.80,
        pastabos=""
    ),
    dict(
        klientas="UAB Klientas A", projektas="Projektas C",
        poz_kodas="DA-0003", poz_pavad="Rėmelis C",
        metalas="Nerūdijantis plienas", plotas="1.80 m2", svoris="4.2 kg",
        kabinimo_budas="Kablys", kabinimas_reme="4-4-3",
        detaliu_kiekis_reme=30, faktinis_kiekis_reme=28,
        paruosimas="Smėliavimas", padengimas="KTL",
        padengimo_standartas="ISO 12944 C4", spalva="RAL7016",
        maskavimas="Kraštai",
        testai_kokybe="", pakavimas="Dėžės",
        instrukcija="Dvigubas sluoksnis kampuose", pakavimo_dienos_norma=100,
        pak_po_ktl=70, pak_po_milt=0, kaina_eur=15.30,
        pastabos="Skubus"
    ),
]

class Command(BaseCommand):
    help = "Sukuria kelis pavyzdinius Pozicija įrašus."

    def handle(self, *args, **kwargs):
        created = 0
        for row in SAMPLE:
            obj, was_created = Pozicija.objects.get_or_create(
                poz_kodas=row["poz_kodas"], defaults=row
            )
            if was_created:
                created += 1
        self.stdout.write(self.style.SUCCESS(f"Sukurta {created} įrašų."))
