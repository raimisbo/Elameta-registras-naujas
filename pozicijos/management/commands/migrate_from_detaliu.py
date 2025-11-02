from django.core.management.base import BaseCommand, CommandError
from django.conf import settings
from django.db import transaction
from django.apps import apps

import json
from pathlib import Path
from decimal import Decimal, InvalidOperation
import re
import sqlite3

from pozicijos.models import Pozicija

FALLBACK_JSON = Path(getattr(settings, "BASE_DIR", Path.cwd())) / "backup_detaliu_registras.json"

# --- Laukų žemėlapis (senas -> naujas) ---
FIELD_MAP = {
    # esminiai
    "kodas": "poz_kodas",
    "pozicijos_kodas": "poz_kodas",
    "poz_kodas": "poz_kodas",

    "pavadinimas": "poz_pavad",
    "poz_pavad": "poz_pavad",

    "klientas": "klientas",
    "projektas": "projektas",

    # specifikacija (pavyzdžiai – plėsk pagal poreikį)
    "metalas": "metalas",
    "plotas": "plotas",
    "svoris": "svoris",
    "spalva": "spalva",
    "danga": "danga",

    # kaina
    "kaina": "kaina_eur",
    "kaina_eur": "kaina_eur",

    # įvairūs
    "pastabos": "pastabos",
}

NUMERIC_FIELDS = {"kaina_eur"}

def _to_decimal(val):
    if val is None or val == "":
        return None
    if isinstance(val, (int, float, Decimal)):
        try:
            return Decimal(str(val))
        except InvalidOperation:
            return None
    s = str(val).strip()
    s = s.replace("€", "").replace("\xa0", "").replace(" ", "")
    s = s.replace(",", ".")
    try:
        return Decimal(s)
    except InvalidOperation:
        return None

def _normalize_record(raw: dict, valid_fields: set) -> dict:
    out = {}
    for k, v in raw.items():
        target = FIELD_MAP.get(k, k)
        if target in valid_fields:
            if target in NUMERIC_FIELDS:
                out[target] = _to_decimal(v)
            else:
                out[target] = "" if v is None else v
    return out

# ---------- ORM iš seno app'o (jei yra) ----------

def _load_from_orm():
    try:
        old_app = apps.get_app_config("detaliu_registras")
    except LookupError:
        return None

    Model = None
    for name in ("Detale", "Pozicija", "Registras", "DetaliuIrasas", "DetaliuPozicija"):
        try:
            Model = apps.get_model("detaliu_registras", name)
            break
        except LookupError:
            continue

    if Model is None:
        models = list(old_app.get_models())
        if not models:
            return None
        Model = models[0]

    fields = [f.name for f in Model._meta.get_fields() if hasattr(f, "attname")]
    qs = Model.objects.all().iterator()
    for obj in qs:
        row = {}
        for f in fields:
            try:
                row[f] = getattr(obj, f, None)
            except Exception:
                row[f] = None
        yield row

# ---------- Tolerantiškas JSON/stream skaitymas ----------

_COMMENT_RE = re.compile(r"(//[^\n\r]*$)|(/\*.*?\*/)", re.MULTILINE | re.DOTALL)
_TRAILING_COMMA_RE = re.compile(r",(\s*[}\]])")
_NON_STD_LITERALS_RE = re.compile(r"\b(NaN|Infinity|-Infinity)\b")

def _strip_bom(text: str) -> str:
    return text.lstrip("\ufeff")

def _clean_json_text(text: str) -> str:
    text = _strip_bom(text)
    text = _COMMENT_RE.sub("", text)
    text = _NON_STD_LITERALS_RE.sub("null", text)
    text = _TRAILING_COMMA_RE.sub(r"\1", text)
    return text.strip()

def _try_parse_standard(text: str):
    return json.loads(text)

def _try_parse_top_object_variants(obj):
    if isinstance(obj, dict):
        for k in ("results", "items", "data", "records"):
            if k in obj and isinstance(obj[k], list):
                return obj[k]
        if "model" in obj and "fields" in obj:
            return [obj]
    return obj

def _iter_json_stream(text: str):
    dec = json.JSONDecoder()
    i, n = 0, len(text)
    while i < n:
        while i < n and text[i].isspace():
            i += 1
        if i >= n:
            break
        try:
            obj, end = dec.raw_decode(text, i)
        except json.JSONDecodeError:
            i += 1
            continue
        yield obj
        i = end

def _load_from_json_forgiving(json_path: Path):
    if not json_path.exists():
        raise FileNotFoundError(f"Nerastas JSON failas: {json_path}")

    raw = json_path.read_text(encoding="utf-8", errors="replace")
    text = _clean_json_text(raw)

    # 1) „kaip yra“
    try:
        data = _try_parse_standard(text)
        data = _try_parse_top_object_variants(data)
        if isinstance(data, list):
            for row in data:
                if isinstance(row, dict):
                    yield row
            return
        if isinstance(data, dict):
            yield data
            return
    except json.JSONDecodeError:
        pass

    # 2) NDJSON
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    parsed_any = False
    for ln in lines:
        try:
            obj = json.loads(ln)
            obj = _try_parse_top_object_variants(obj)
            if isinstance(obj, list):
                for row in obj:
                    if isinstance(row, dict):
                        yield row
                        parsed_any = True
            elif isinstance(obj, dict):
                yield obj
                parsed_any = True
        except json.JSONDecodeError:
            continue
    if parsed_any:
        return

    # 3) „stream“ su raw_decode
    parsed_any = False
    for obj in _iter_json_stream(text):
        obj = _try_parse_top_object_variants(obj)
        if isinstance(obj, list):
            for row in obj:
                if isinstance(row, dict):
                    yield row
                    parsed_any = True
        elif isinstance(obj, dict):
            yield obj
            parsed_any = True
    if parsed_any:
        return

    # 4) klaida su kontekstu
    try:
        json.loads(text)
    except json.JSONDecodeError as e:
        pos = e.pos
        start = max(0, pos - 120)
        end = min(len(text), pos + 120)
        context = text[start:end]
        raise ValueError(
            f"JSON nepavyko perskaityti ({json_path}).\n"
            f"Klaida: {e}\n"
            f"Kontekstas apie poziciją {pos}:\n---\n{context}\n---"
        ) from e

def _load_from_json(json_path: Path):
    yield from _load_from_json_forgiving(json_path)

# ---------- Skaitymas tiesiai iš seno SQLite ----------

def _quote_ident(name: str) -> str:
    # SQLite identifikatorių citavimas su dvigubomis kabutėmis, pabėgant pačias kabutes
    return '"' + str(name).replace('"', '""') + '"'

def _load_from_sqlite(db_path: Path, table: str, columns=None, where=None):
    """
    Skaito eilutes tiesiai iš seno SQLite.
    - Patikrina, ar lentelė egzistuoja.
    - Jei columns nenurodytas -> ima visus.
    - Saugiai cituoja identifikatorius.
    """
    if not db_path.exists():
        raise FileNotFoundError(f"Nerastas SQLite failas: {db_path}")

    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    try:
        cur = conn.cursor()

        # 1) Ar lentelė egzistuoja?
        cur.execute("""
            SELECT name FROM sqlite_master
            WHERE type IN ('table','view') AND name = ?
        """, (table,))
        row = cur.fetchone()
        if not row:
            # Parodom, kas yra DB
            cur.execute("SELECT name FROM sqlite_master WHERE type IN ('table','view') ORDER BY name")
            existing = [r[0] for r in cur.fetchall()]
            raise ValueError(
                f"Lentelė '{table}' nerasta SQLite faile {db_path}.\n"
                f"Galimos lentelės/vaizdai: {', '.join(existing) or '(nėra)'}"
            )

        # 2) Išsiaiškinam visus stulpelius
        cur.execute(f"PRAGMA table_info({_quote_ident(table)})")
        all_cols = [r[1] for r in cur.fetchall()]  # r[1] = name
        if not all_cols:
            raise ValueError(f"Lentelė '{table}' neturi stulpelių (arba nėra prieinama).")

        # 3) Kurį sąrašą naudoti?
        if not columns:
            cols = all_cols
        else:
            requested = [c.strip() for c in columns.split(",") if c.strip()]
            # paliekam tik egzistuojančius
            cols = [c for c in requested if c in all_cols]
            missing = [c for c in requested if c not in all_cols]
            if missing:
                raise ValueError(
                    f"Šie stulpeliai nerasti lentelėje '{table}': {', '.join(missing)}.\n"
                    f"Galimi stulpeliai: {', '.join(all_cols)}"
                )
            if not cols:
                raise ValueError(
                    f"Nenurodytas nė vienas galiojantis stulpelis lentelėje '{table}'. "
                    f"Galimi: {', '.join(all_cols)}"
                )

        # 4) Sudarom SQL saugiai
        cols_sql = ", ".join(_quote_ident(c) for c in cols)
        sql = f"SELECT {cols_sql} FROM {_quote_ident(table)}"
        if where and where.strip():
            sql += f" WHERE {where}"

        for row in cur.execute(sql):
            yield {k: row[k] for k in cols}

    finally:
        conn.close()

# --------------------------------------------------

class Command(BaseCommand):
    help = "Importuoja senus detalių/pozicijų duomenis į naują 'pozicijos.Pozicija' modelį (JSON / ORM / SQLite)."

    def add_arguments(self, parser):
        parser.add_argument("--dry-run", action="store_true", help="Nieko neįrašo, tik suvestinė.")
        parser.add_argument("--reset", action="store_true", help="Prieš importą išvalo 'Pozicija' lentelę.")
        parser.add_argument("--limit", type=int, default=None, help="Importuoti tik N pirmų įrašų.")
        parser.add_argument("--source", choices=["orm", "json", "sqlite"], default=None,
                            help="Šaltinis: ORM, JSON arba SQLite.")
        parser.add_argument("--json-path", type=str, default=None,
                            help=f"JSON kelias (numatytas: {FALLBACK_JSON})")

        # SQLite parametrai
        parser.add_argument("--sqlite", type=str, default=None, help="Kelias iki seno SQLite DB (pvz., db.sqlite3.bak_...).")
        parser.add_argument("--table", type=str, default=None, help="Lentelės pavadinimas senoje DB (pvz., 'detales' arba 'pozicijos').")
        parser.add_argument("--columns", type=str, default=None, help="Pasirenkami stulpeliai (kableliais atskirtas sąrašas).")
        parser.add_argument("--where", type=str, default=None, help="SQL WHERE filtras (pvz., \"kodas IS NOT NULL\").")

        # Raktas (šaltinio laukas) – kuris laikomas pozicijos kodu
        parser.add_argument("--key", type=str, default=None, help="Upsert raktas šaltinyje (pvz., 'kodas').")

    def handle(self, *args, **opts):
        dry = opts["dry_run"]
        reset = opts["reset"]
        limit = opts["limit"]
        source = opts["source"]
        json_path = Path(opts["json_path"]) if opts.get("json_path") else FALLBACK_JSON
        key_from_cli = opts.get("key")

        sqlite_path = Path(opts["sqlite"]) if opts.get("sqlite") else None
        table = opts.get("table")
        columns = opts.get("columns")
        where = opts.get("where")

        valid_fields = {f.name for f in Pozicija._meta.get_fields() if hasattr(f, "attname")}
        key_field = "poz_kodas"
        if key_field not in valid_fields:
            raise CommandError("Modelyje 'Pozicija' nėra lauko 'poz_kodas' – būtinas upsert raktas.")

        # Šaltinio pasirinkimas
        if source == "orm":
            loader = _load_from_orm() or []
            src_label = "ORM"
        elif source == "json":
            loader = _load_from_json(json_path)
            src_label = f"JSON ({json_path})"
        elif source == "sqlite":
            if not sqlite_path or not table:
                raise CommandError("SQLite režime privaloma nurodyti --sqlite ir --table.")
            loader = _load_from_sqlite(sqlite_path, table, columns=columns, where=where)
            src_label = f"SQLite ({sqlite_path} :: {table})"
        else:
            # AUTO: pirma ORM, tada JSON, tada jei nurodytas --sqlite – SQLite
            loader = _load_from_orm()
            src_label = "AUTO (ORM->JSON)"
            if loader is None:
                loader = _load_from_json(json_path)
                src_label = f"AUTO->JSON ({json_path})"
            if sqlite_path and table:
                # jei visai tuščia – bandys SQLite
                # Pastaba: specialiai neperrašau, kad svetimo auto nepadarytų netikėtai
                pass

        stats = {"seen": 0, "created": 0, "updated": 0, "skipped_no_key": 0, "errors": 0}
        skipped_logged = 0

        if reset and not dry:
            self.stdout.write(self.style.WARNING("Išvalau 'Pozicija' lentelę (reset)..."))
            Pozicija.objects.all().delete()

        self.stdout.write(self.style.MIGRATE_HEADING("Pradedu importą į 'pozicijos.Pozicija'"))
        self.stdout.write(f"Šaltinis: {src_label}")
        if key_from_cli:
            self.stdout.write(f"Raktas (šaltinio laukas): {key_from_cli}")
        if limit:
            self.stdout.write(f"Limitas: {limit}")

        try:
            with transaction.atomic():
                for i, raw in enumerate(loader, start=1):
                    if limit and i > limit:
                        break
                    stats["seen"] += 1

                    # Jei tai Django fixture objektas su "fields" – imam būtent fields
                    if isinstance(raw, dict) and "fields" in raw:
                        payload = raw["fields"]
                    else:
                        payload = raw

                    if not isinstance(payload, dict):
                        stats["errors"] += 1
                        self.stderr.write(self.style.ERROR(f"#{i} neatpažintas įrašas: {type(payload)}"))
                        continue

                    rec = _normalize_record(payload, valid_fields)

                    # --- raktas ---
                    key = None
                    if key_from_cli:
                        key = payload.get(key_from_cli) or raw.get(key_from_cli) if isinstance(raw, dict) else None
                    if not key:
                        for nm in ("poz_kodas","kodas","pozicijos_kodas","pozicijosNr","poz_nr","kodas_pozicijos"):
                            key = payload.get(nm) if isinstance(payload, dict) else None
                            if not key and isinstance(raw, dict):
                                key = raw.get(nm)
                            if key:
                                break

                    if not key or str(key).strip() == "":
                        stats["skipped_no_key"] += 1
                        if skipped_logged < 3:
                            skipped_logged += 1
                            self.stderr.write(self.style.WARNING(
                                f"#{i} praleistas: nerastas raktas. Galimi laukai: {', '.join(sorted(payload.keys())) or '(nėra)'}\n"
                                f"Patarimas: nurodyk raktą: --key kodas (arba realus pavadinimas tavo lentelėje)."
                            ))
                        continue

                    defaults = rec.copy()
                    defaults.pop(key_field, None)
                    # jei raktas buvo ne 'poz_kodas', užpildom modelio lauką
                    if key_field not in rec:
                        defaults[key_field] = str(key)

                    try:
                        obj, created = Pozicija.objects.update_or_create(
                            **{key_field: key},
                            defaults=defaults
                        )
                        if created:
                            stats["created"] += 1
                        else:
                            stats["updated"] += 1
                    except Exception as e:
                        stats["errors"] += 1
                        self.stderr.write(self.style.ERROR(f"#{i} klaida (key={key!r}): {e}"))

                if dry:
                    raise RuntimeError("DRY_RUN")  # rollback

        except RuntimeError as r:
            if str(r) != "DRY_RUN":
                raise
            self.stdout.write(self.style.WARNING("Dry-run režimas: pakeitimai neįrašyti."))

        self.stdout.write("")
        self.stdout.write(self.style.SUCCESS("✓ Importo suvestinė"))
        for k, v in stats.items():
            self.stdout.write(f"  {k}: {v}")
