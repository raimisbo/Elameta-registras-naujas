import csv
from io import StringIO
from datetime import datetime
from .models import Klientas, Projektas, Detale, Kaina, Danga, Uzklausa

def parse_int(value):
    try:
        return int(float(value)) if value else 0
    except (ValueError, TypeError):
        return 0

def import_csv(file):
    file.seek(0)
    encoding = 'utf-8'
    csv_file = file.read().decode(encoding)
    csv_file = StringIO(csv_file)
    reader = csv.DictReader(csv_file)

    klaidos = []

    for i, row in enumerate(reader, start=1):
        try:
            # Klientas
            kliento_vardas = row.get('klientas_pavadinimas')
            if not kliento_vardas:
                klaidos.append(f"Eilutė {i}: Trūksta kliento pavadinimo.")
                continue

            klientas, _ = Klientas.objects.update_or_create(
                vardas=kliento_vardas.strip()
            )

            # Projektas
            projektas, _ = Projektas.objects.update_or_create(
                pavadinimas=row.get('projektas_pavadinimas'),
                defaults={
                    'klientas': klientas,
                    'uzklausos_data': row.get('uzklausos_data') or None,
                    'pasiulymo_data': row.get('pasiulymo_data') or None,
                }
            )

            # Detalė
            detale, _ = Detale.objects.update_or_create(
                brezinio_nr=row.get('detale_brezinio_nr'),
                defaults={
                    'pavadinimas': row.get('detale_pavadinimas'),
                    'plotas': row.get('detale_plotas'),
                    'svoris': row.get('detale_svoris'),
                    'kiekis_metinis': parse_int(row.get('detale_kiekis_metinis')),
                    'kiekis_menesis': parse_int(row.get('detale_kiekis_menesis')),
                    'kiekis_partijai': parse_int(row.get('detale_kiekis_partijai')),
                    'standartas': row.get('detale_standartas'),
                    'kabinimo_tipas': row.get('detale_kabinimo_tipas'),
                    'kabinimas_xyz': row.get('detale_kabinimas_xyz'),
                    'kiekis_reme': parse_int(row.get('detale_kiekis_reme')),
                    'faktinis_kiekis_reme': parse_int(row.get('detale_faktinis_kiekis_reme')),
                    'pakavimas': row.get('detale_pakavimas'),
                    'nuoroda_brezinio': row.get('detale_nuoroda_brezinio'),
                    'nuoroda_pasiulymo': row.get('detale_nuoroda_pasiulymo'),
                    'pastabos': row.get('detale_pastabos'),
                    'projektas': projektas,
                }
            )

            # Dangos
            if row.get('detale_danga'):
                danga_pavadinimai = [d.strip() for d in row['detale_danga'].split(',')]
                dangos = Danga.objects.filter(pavadinimas__in=danga_pavadinimai)
                detale.danga.set(dangos)

            # Kaina
            if row.get('kaina_suma'):
                try:
                    suma = float(row.get('kaina_suma'))
                except ValueError:
                    suma = 0.0

                Kaina.objects.update_or_create(
                    detalė=detale,
                    fiksuotas_kiekis=row.get('kaina_fiksuotas_kiekis'),
                    defaults={
                        'busena': row.get('kaina_busena'),
                        'suma': suma,
                        'kiekis_nuo': parse_int(row.get('kaina_kiekis_nuo')),
                        'kiekis_iki': parse_int(row.get('kaina_kiekis_iki')),
                    }
                )

            # Užklausa
            Uzklausa.objects.get_or_create(
                klientas=klientas,
                projektas=projektas,
                detale=detale,
            )

        except Exception as e:
            klaidos.append(f"Eilutė {i}: Klaida importuojant - {str(e)}")

    return klaidos
