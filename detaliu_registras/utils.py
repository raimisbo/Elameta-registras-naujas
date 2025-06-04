import csv
from io import StringIO
from .models import Klientas, Projektas, Detale, Kaina, Danga, Uzklausa

def parse_int(value):
    try:
        return int(value) if value else 0
    except ValueError:
        return 0

def import_csv(file):
    file.seek(0)  # Užtikrina, kad pradedame skaityti nuo pradžios
    encoding = 'utf-8'
    csv_file = file.read().decode(encoding)
    
    # Panaudokite StringIO, kad imituotumėte failą
    csv_file = StringIO(csv_file)
    
    # Naudokite DictReader, kad perskaitytumėte CSV
    reader = csv.DictReader(csv_file)
    
    for row in reader:
        # Importuojame Klientą
        klientas, _ = Klientas.objects.update_or_create(
            vardas=row.get('klientas_pavadinimas'),
            
        )

        # Importuojame Projektą
        projektas, _ = Projektas.objects.update_or_create(
            pavadinimas=row.get('projektas_pavadinimas'),
            defaults={
                'klientas': klientas,
                'uzklausos_data': row.get('uzklausos_data'),
                'pasiulymo_data': row.get('pasiulymo_data'),
            }
        )
        
        
        # Importuojame Detalę
        detale, _ = Detale.objects.update_or_create(
            brezinio_nr=row.get('detale_brezinio_nr'),
            defaults={
                'pavadinimas': row.get('detale_pavadinimas'),
                'plotas': row.get('detale_plotas'),
                'svoris': row.get('detale_svoris'),
                'kiekis_metinis': row.get('detale_kiekis_metinis'),
                'kiekis_menesis': row.get('detale_kiekis_menesis'),
                'kiekis_partijai': row.get('detale_kiekis_partijai'),
                'standartas': row.get('detale_standartas'),
                'kabinimo_tipas': row.get('detale_kabinimo_tipas'),
                'kabinimas_xyz': row.get('detale_kabinimas_xyz'),
                'kiekis_reme': row.get('detale_kiekis_reme'),
                'faktinis_kiekis_reme': parse_int(row.get('detale_faktinis_kiekis_reme')),
                'pakavimas': row.get('detale_pakavimas'),
                'nuoroda_brezinio': row.get('detale_nuoroda_brezinio'),
                'nuoroda_pasiulymo': row.get('detale_nuoroda_pasiulymo'),
                'pastabos': row.get('detale_pastabos'),
                'projektas': projektas
            }
        )
        if 'detale_danga' in row:
            danga_pavadinimai = row['detale_danga'].split(',')
            dangos = Danga.objects.filter(pavadinimas__in=danga_pavadinimai)
            detale.danga.set(dangos)
            
        # Importuojame Kainą
        kaina, _ = Kaina.objects.update_or_create(
            detalė=detale,
            fiksuotas_kiekis=row.get('kaina_fiksuotas_kiekis'),
            defaults={
                'busena': row.get('kaina_busena'),
                'suma': float(row.get('kaina_suma', 0.00)),
                'kiekis_nuo': parse_int(row.get('kaina_kiekis_nuo')),
                'kiekis_iki': parse_int(row.get('kaina_kiekis_iki')),
            }
        )
        Uzklausa.objects.get_or_create(
                        klientas=klientas,
                        projektas=projektas,
                        detale=detale,
                    )