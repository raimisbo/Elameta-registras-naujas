# pozicijos/schemas/columns.py

COLUMNS = [
    # --- Pagrindiniai ---
    {"key": "klientas",  "label": "Klientas",  "type": "text",   "filter": "text",  "searchable": True,  "width": 180, "default": True},
    {"key": "projektas", "label": "Projektas", "type": "text",   "filter": "text",  "searchable": True,  "width": 200, "default": False},
    {"key": "poz_kodas", "label": "Kodas",     "type": "text",   "filter": "text",  "searchable": True,  "width": 140, "default": True},
    {"key": "poz_pavad", "label": "Pavadinimas", "type": "text", "filter": "text",  "searchable": True,  "width": 280, "default": True},

    # --- Brėžiniai (kol kas virtual) ---
    {"key": "brez_count", "label": "Brėžinys", "type": "virtual", "filter": None,   "searchable": False, "width": 110, "default": False},

    # --- Specifikacija ---
    {"key": "metalas",    "label": "Metalas",   "type": "text",   "filter": "text",  "searchable": True,  "width": 120, "default": False},
    {"key": "plotas",     "label": "Plotas",    "type": "text",   "filter": "text",  "searchable": True,  "width": 100, "default": False},
    {"key": "svoris",     "label": "Svoris",    "type": "text",   "filter": "text",  "searchable": True,  "width": 100, "default": False},

    # --- Kabinimas ---
    {"key": "kabinimo_budas",      "label": "Kabinimo būdas", "type": "text",  "filter": "text",  "searchable": True,  "width": 160, "default": False},
    {"key": "kabinimas_reme",      "label": "Kabinimas rėme", "type": "text",  "filter": "text",  "searchable": True,  "width": 160, "default": False},
    {"key": "detaliu_kiekis_reme", "label": "Detalių/rėme",   "type": "number","filter": "range", "searchable": False, "width": 110, "default": False},
    {"key": "faktinis_kiekis_reme","label": "Faktinis/rėme",  "type": "number","filter": "range", "searchable": False, "width": 110, "default": False},

    # --- Paviršius / dažymas ---
    {"key": "paruosimas",           "label": "Paruošimas",        "type": "text", "filter": "text",  "searchable": True, "width": 150, "default": False},
    {"key": "padengimas",           "label": "Padengimas",        "type": "text", "filter": "text",  "searchable": True, "width": 150, "default": False},
    {"key": "padengimo_standartas", "label": "Standartas",        "type": "text", "filter": "text",  "searchable": True, "width": 140, "default": False},
    {"key": "spalva",               "label": "Spalva",            "type": "text", "filter": "text",  "searchable": True, "width": 100, "default": False},
    {"key": "maskavimas",           "label": "Maskavimas",        "type": "text", "filter": "text",  "searchable": True, "width": 160, "default": False},
    {"key": "testai_kokybe",        "label": "Testai/kokybė",     "type": "text", "filter": "text",  "searchable": True, "width": 180, "default": False},

    # --- Terminai ---
    {"key": "atlikimo_terminas", "label": "Atlikimo terminas", "type": "date",   "filter": "date",  "searchable": False, "width": 140, "default": False},

    # --- Pakavimas ---
    {"key": "pakavimas",            "label": "Pakavimas",          "type": "text",   "filter": "text",  "searchable": True,  "width": 160, "default": False},
    {"key": "instrukcija",          "label": "Instrukcija",        "type": "text",   "filter": "text",  "searchable": True,  "width": 180, "default": False},
    {"key": "pakavimo_dienos_norma","label": "Pakav. d. norma",    "type": "number", "filter": "range", "searchable": False, "width": 140, "default": False},
    {"key": "pak_po_ktl",           "label": "Pak. po KTL",        "type": "number", "filter": "range", "searchable": False, "width": 130, "default": False},
    {"key": "pak_po_milt",          "label": "Pak. po milt",       "type": "number", "filter": "range", "searchable": False, "width": 130, "default": False},

    # --- Kaina ---
    {"key": "kaina_eur", "label": "Kaina", "type": "number", "filter": "range", "searchable": False, "width": 120, "default": False},

    # --- Dokumentai / pastabos (virtualus + tekstas) ---
    {"key": "dok_count", "label": "Dokumentai", "type": "virtual", "filter": None,  "searchable": False, "width": 120, "default": False},
    {"key": "pastabos",  "label": "Pastabos",   "type": "text",    "filter": "text","searchable": True,  "width": 240, "default": False},
]
