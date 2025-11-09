# pozicijos/management/commands/import_sena_db.py
import sqlite3
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError

from pozicijos.models import Pozicija, PozicijosKaina


class Command(BaseCommand):
    help = "Importuoja seną detalių registro DB (SQLite) į naują pozicijų struktūrą."

    def add_arguments(self, parser):
        parser.add_argument(
            "--db",
            dest="db_path",
            required=True,
            help="Kelias iki seno db.sqlite3 failo",
        )

    def handle(self, *args, **options):
        db_path = options["db_path"]
        db_file = Path(db_path)
        if not db_file.exists():
            raise CommandError(f"Failas nerastas: {db_file}")

        self.stdout.write(self.style.NOTICE(f"Jungiuosi prie {db_file} ..."))
        conn = sqlite3.connect(str(db_file))
        cur = conn.cursor()

        # pasiimam visas detales
        cur.execute("SELECT id, pavadinimas, brezinio_nr, plotas, svoris, pakavimas, pastabos, projektas_id FROM detaliu_registras_detale")
        detales = cur.fetchall()

        # pasiruošiam žemėlapius klientams ir projektams
        cur.execute("SELECT id, vardas FROM detaliu_registras_klientas")
        klientai = {row[0]: row[1] for row in cur.fetchall()}

        cur.execute("SELECT id, pavadinimas, klientas_id FROM detaliu_registras_projektas")
        projektai = {}
        for row in cur.fetchall():
            proj_id, pavad, kl_id = row
            projektai[proj_id] = {
                "pavadinimas": pavad,
                "klientas": klientai.get(kl_id, None),
            }

        imported = 0
        for detale in detales:
            (
                d_id,
                pavadinimas,
                brezinio_nr,
                plotas,
                svoris,
                pakavimas,
                pastabos,
                projektas_id,
            ) = detale

            # susirandam projektą ir klientą pagal projektą
            proj = projektai.get(projektas_id, {})
            projektas_pav = proj.get("pavadinimas")
            klientas_pav = proj.get("klientas")

            # sukuriam naują Pozicija
            poz = Pozicija.objects.create(
                klientas=klientas_pav,
                projektas=projektas_pav,
                poz_kodas=brezinio_nr or f"DET-{d_id}",
                poz_pavad=pavadinimas,
                plotas=plotas or None,
                svoris=svoris or None,
                pakavimas=pakavimas or "",
                pastabos=pastabos or "",
            )

            # dabar – kainos šitai detalei
            # senoje DB stulpelio vardas yra su lietuviška raide: "detalė_id"
            # dėl to SELECT'e jį kabutėse rašom
            cur.execute(
                'SELECT id, busena, suma, yra_fiksuota, kiekis_nuo, kiekis_iki, fiksuotas_kiekis, kainos_matas '
                'FROM detaliu_registras_kaina WHERE "detalė_id" = ?',
                (d_id,),
            )
            kainos = cur.fetchall()
            last_actual = None
            for k in kainos:
                (
                    k_id,
                    busena,
                    suma,
                    yra_fiksuota,
                    kiekis_nuo,
                    kiekis_iki,
                    fiksuotas_kiekis,
                    kainos_matas,
                ) = k
                k_obj = PozicijosKaina.objects.create(
                    pozicija=poz,
                    suma=suma or 0,
                    busena=busena or "aktuali",
                    yra_fiksuota=bool(yra_fiksuota),
                    kiekis_nuo=kiekis_nuo,
                    kiekis_iki=kiekis_iki,
                    fiksuotas_kiekis=fiksuotas_kiekis,
                    kainos_matas=kainos_matas or "vnt.",
                )
                if k_obj.busena == "aktuali":
                    last_actual = k_obj

            # jei buvo aktuali – perkeliam į pozicijos lauką
            if last_actual:
                poz.kaina_eur = last_actual.suma
                poz.save(update_fields=["kaina_eur"])

            imported += 1

        conn.close()
        self.stdout.write(self.style.SUCCESS(f"Importuota pozicijų: {imported}"))
