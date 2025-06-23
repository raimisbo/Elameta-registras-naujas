import csv
from io import StringIO
from .models import Klientas, Projektas, Detale, Kaina, Danga, Uzklausa

def parse_int(value):
    try:
        return int(float(value)) if value else 0
    except (ValueError, TypeError):
        return 0

def parse_date(date_str):
    from datetime import datetime
    if not date_str:
        return None
    for fmt in ('%Y-%m-%d', '%d.%m.%Y', '%Y/%m/%d'):
        try:
            return datetime.strptime(date_str, fmt).date()
        except ValueError:
            continue
    return None  # jei neatitinka nei vieno formato

from io import StringIO
import csv
from .models import Klientas, Projektas, Detale, Danga, Kaina, Uzklausa
from datetime import datetime

def parse_int(value):
    try:
        return int(float(value)) if value else 0
    except (ValueError, TypeError):
        return 0

def parse_date(value):
    try:
        return datetime.strptime(value, "%Y-%m-%d").date() if value else None
    except (ValueError, TypeError):
        return None

def import_csv(file):
    klaidos = []

    file.seek(0)
    raw_data = file.read().decode('utf-8')
    csv_file = StringIO(raw_data, newline='')

    # Bandome aptikti kabliataškį kaip atskyriklį
    try:
        sniffer = csv.Sniffer()
        dialect = sniffer.sniff(raw_data[:1024])
        dialect.delimiter = ';'  # Perrašome delimiterį į kabliataškį
    except csv.Error:
        dialect = csv.excel
        dialect.delimiter = ';'

    reader = csv.DictReader(csv_file, dialect=dialect)

    for i, row in enumerate(reader, start=2):  # Pradedame nuo 2, nes 1 – antraštė
        try:
            # --- Klientas ---
            kliento_vardas = row.get('klientas_pavadinimas')
            if not kliento_vardas:
                klaidos.append(f"Eilutė {i}: Trūksta kliento pavadinimo.")
                continue

            klientas, _ = Klientas.objects.update_or_create(
                vardas=kliento_vardas.strip()
            )

            # --- Projektas ---
            projektas_pavadinimas = row.get('projektas_pavadinimas')
            if not projektas_pavadinimas:
                klaidos.append(f"Eilutė {i}: Trūksta projekto pavadinimo.")
                continue

            uzklausos_data = parse_date(row.get('uzklausos_data'))
            if uzklausos_data is None:
                klaidos.append(f"Eilutė {i}: Trūksta arba blogas 'uzklausos_data' formatas.")
                continue

            projektas, _ = Projektas.objects.update_or_create(
                pavadinimas=projektas_pavadinimas.strip(),
                defaults={
                    'klientas': klientas,
                    'uzklausos_data': uzklausos_data,
                    'pasiulymo_data': parse_date(row.get('pasiulymo_data')),
                }
            )

            # --- Detalė ---
            detale, _ = Detale.objects.update_or_create(
                brezinio_nr=row.get('detale_brezinio_nr'),
                defaults={
                    'pavadinimas': row.get('detale_pavadinimas'),
                    'plotas': float(row.get('detale_plotas') or 0),
                    'svoris': float(row.get('detale_svoris') or 0),
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
                    'ppap_dokumentai': row.get('ppap_dokumentai') or '',
                    'projektas': projektas,
                }
            )

            # --- Danga ---
            if 'detale_danga' in row and row['detale_danga']:
                danga_pavadinimai = [d.strip() for d in row['detale_danga'].split(',')]
                dangos = Danga.objects.filter(pavadinimas__in=danga_pavadinimai)
                detale.danga.set(dangos)

            # --- Kaina ---
            try:
                kaina_suma = float(row.get('kaina_suma')) if row.get('kaina_suma') else 0.0
            except ValueError:
                kaina_suma = 0.0

            Kaina.objects.update_or_create(
                detalė=detale,
                fiksuotas_kiekis=parse_int(row.get('kaina_fiksuotas_kiekis')),
                defaults={
                    'busena': row.get('kaina_busena'),
                    'suma': kaina_suma,
                    'kiekis_nuo': parse_int(row.get('kaina_kiekis_nuo')),
                    'kiekis_iki': parse_int(row.get('kaina_kiekis_iki')),
                    'yra_fiksuota': True if row.get('kaina_busena') == 'aktuali' else False,
                    'kainos_matas': row.get('kainos_matas') or 'vnt.',
                }
            )

            # --- Užklausa ---
            Uzklausa.objects.get_or_create(
                klientas=klientas,
                projektas=projektas,
                detale=detale,
            )

        except Exception as e:
            klaidos.append(f"Eilutė {i}: Klaida importuojant - {str(e)}")

    return klaidos