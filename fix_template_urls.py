# -*- coding: utf-8 -*-
"""
Vietinis šablonų URL'ų tvarkytojas.
Naudojimas: python3 fix_template_urls.py
- Pereina per visus .html, pataiso {% url '...' %} kvietimus.
- Kuria .bak kopijas tik jei failas realiai keičiamas.
- Išveda suvestinę ir sukuria CSV 'templates_url_replacements.csv'.
"""

import re, sys, os, csv
from pathlib import Path
from datetime import datetime

ROOT = Path.cwd()
TEMPLATES = list(ROOT.rglob("*.html"))

# Kanoniniai vardai su teisingais namespace'ais
CANONICAL = {
    "uzklausa_list": "detaliu_registras:uzklausa_list",
    "ivesti_uzklausa": "detaliu_registras:ivesti_uzklausa",
    "redaguoti_uzklausa": "detaliu_registras:redaguoti_uzklausa",
    "perziureti_uzklausa": "detaliu_registras:perziureti_uzklausa",
    "redaguoti_kaina": "detaliu_registras:redaguoti_kaina",
    "prideti_kaina": "detaliu_registras:prideti_kaina",
    "import_uzklausos": "detaliu_registras:import_uzklausos",
}
HISTORY = {
    "history_partial": "detaliu_registras_history:history_partial",
}

def norm(s: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", s.lower())

SYNONYMS = {
    # list
    "uzklausos": "uzklausa_list",
    "uzklausulistas": "uzklausa_list",
    "uzklausulist": "uzklausa_list",
    "list": "uzklausa_list",
    "sarasas": "uzklausa_list",
    "perziuretiuzklausas": "uzklausa_list",
    # create
    "ivestiuzklausa": "ivesti_uzklausa",
    "naujauzklausa": "ivesti_uzklausa",
    "sukurtiuzklausa": "ivesti_uzklausa",
    "uzklausacreate": "ivesti_uzklausa",
    "createuzklausa": "ivesti_uzklausa",
    # update
    "redaguotiuzklausa": "redaguoti_uzklausa",
    "uzklausaupdate": "redaguoti_uzklausa",
    "updateuzklausa": "redaguoti_uzklausa",
    "edituzklausa": "redaguoti_uzklausa",
    # detail
    "perziuretiuzklausa": "perziureti_uzklausa",
    "uzklausadetail": "perziureti_uzklausa",
    "detailuzklausa": "perziureti_uzklausa",
    "viewuzklausa": "perziureti_uzklausa",
    # price
    "redaguotikaina": "redaguoti_kaina",
    "kainaupdate": "redaguoti_kaina",
    "updatekaina": "redaguoti_kaina",
    "kainosupdate": "redaguoti_kaina",
    "pridetikaina": "prideti_kaina",
    "kainacreate": "prideti_kaina",
    "kainoscreate": "prideti_kaina",
    "newkaina": "prideti_kaina",
    # import
    "importas": "import_uzklausos",
    "import": "import_uzklausos",
    "importcsv": "import_uzklausos",
    "importuzklausos": "import_uzklausos",
}

CANONICAL_NORMS = {norm(k): k for k in CANONICAL.keys()}

# {% url 'name' %} arba {% url "name" %}
URL_TAG_RE = re.compile(r"({%\s*url\s+)(['\"])(?P<name>[^'\"]+)\2")

def rewrite_name(name: str) -> str | None:
    # Jau istorijos namespace?
    if name.startswith("detaliu_registras_history:"):
        short = name.split(":", 1)[1]
        target = HISTORY.get(short)
        return target if target and target != name else None
    # Jau pagr. namespace?
    if name.startswith("detaliu_registras:"):
        short = name.split(":", 1)[1]
        if short in CANONICAL:
            return CANONICAL[short] if CANONICAL[short] != name else None
        nrm = norm(short)
        if nrm in SYNONYMS:
            return CANONICAL[SYNONYMS[nrm]]
        return None
    # Be namespace
    nrm = norm(name)
    if nrm in CANONICAL_NORMS:
        return CANONICAL[CANONICAL_NORMS[nrm]]
    if nrm in SYNONYMS:
        return CANONICAL[SYNONYMS[nrm]]
    if "history" in nrm and "partial" in nrm:
        return HISTORY["history_partial"]
    return None

def process_text(text: str, relpath: str, changes: list) -> str:
    out, pos = [], 0
    for m in URL_TAG_RE.finditer(text):
        out.append(text[pos:m.start()])
        tag_open, quote, old = m.group(1), m.group(2), m.group("name").strip()
        new = rewrite_name(old)
        if new:
            out.append(f"{tag_open}{quote}{new}{quote}")
            changes.append({"file": relpath, "from": old, "to": new})
        else:
            out.append(text[m.start():m.end()])
        pos = m.end()
    out.append(text[pos:])
    return "".join(out)

def main():
    changes = []
    changed_files = 0
    for p in TEMPLATES:
        rel = str(p.relative_to(ROOT))
        try:
            txt = p.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            txt = p.read_text(errors="ignore")
        new_txt = process_text(txt, rel, changes)
        if new_txt != txt:
            # backup tik jei keičiam
            bak = p.with_suffix(p.suffix + ".bak")
            p.replace(bak)          # perkeliam seną -> .bak
            p.write_text(new_txt, encoding="utf-8")
            changed_files += 1
    # CSV suvestinė
    if changes:
        with open("templates_url_replacements.csv", "w", newline="", encoding="utf-8") as fh:
            w = csv.DictWriter(fh, fieldnames=["file","from","to"])
            w.writeheader()
            for row in changes:
                w.writerow(row)

    print("===== ŠABLONŲ URL TVARKYMAS =====")
    print(f"Bendras .html kiekis: {len(TEMPLATES)}")
    print(f"Pakeistų failų:       {changed_files}")
    print(f"Pakeitimų įrašų:      {len(changes)}")
    if changes:
        print("Suvestinė: templates_url_replacements.csv")
    print("Atlikta.")

if __name__ == "__main__":
    main()
