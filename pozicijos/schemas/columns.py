# pozicijos/schemas/columns.py

COLUMNS = [
    # ===========================
    # [Pagrindiniai]
    # ===========================
    {"key": "klientas",  "label": "Klientas",  "type": "text",   "filter": "text",   "searchable": True,  "width": 180, "default": False},
    {"key": "projektas", "label": "Projektas", "type": "text",   "filter": "text",   "searchable": True,  "width": 200, "default": False},
    {"key": "poz_kodas", "label": "Kodas",     "type": "text",   "filter": "text",   "searchable": True,  "width": 140, "default": True},

    # ===========================
    # [Detalė]
    # ===========================
    {"key": "poz_pavad",  "label": "Pavadinimas", "type": "text",    "filter": "text",   "searchable": True,  "width": 280, "default": True},
    {"key": "brez_count", "label": "Brėžinys",    "type": "virtual", "filter": None,     "searchable": False, "width": 110, "default": False},

    # ===========================
    # [Specifikacija]
    # ===========================
    {"key": "metalas", "label": "Metalas", "type": "text", "filter": "text", "searchable": True,  "width": 140, "default": False},
    {"key": "plotas",  "label": "Plotas",  "type": "text", "filter": "text", "searchable": True,  "width": 120, "default": False},
    {"key": "svoris",  "label": "Svoris",  "type": "text", "filter": "text", "searchable": True,  "width": 120, "default": False},

    # ===========================
    # [Kabinimas]
    # ===========================
    {"key": "kabinimo_budas",      "label": "Kabinimo būdas",        "type": "text",   "filter": "text",  "searchable": True,  "width": 160, "default": False},
    {"key": "kabinimas_reme",      "label": "Kabinimas rėme x-y-z",  "type": "text",   "filter": "text",  "searchable": True,  "width": 160, "default": False},
    {"key": "detaliu_kiekis_reme", "label": "Detalių kiekis rėme",   "type": "number", "filter": "range", "searchable": False, "width": 150, "default": False},
    {"key": "faktinis_kiekis_reme","label": "Faktinis kiekis rėme",  "type": "number", "filter": "range", "searchable": False, "width": 160, "default": False},

    # ===========================
    # [Dažymas]
    # ===========================
    {"key": "paruosimas",           "label": "Paruošimas",           "type": "text",   "filter": "text",  "searchable": True,  "width": 160, "default": False},
    {"key": "padengimas",           "label": "Padengimas",           "type": "text",   "filter": "text",  "searchable": True,  "width": 150, "default": False},
    {"key": "padengimo_standartas", "label": "Padengimo standartas", "type": "text",   "filter": "text",  "searchable": True,  "width": 180, "default": False},
    {"key": "spalva",               "label": "Spalva",               "type": "choice", "filter": "select","searchable": True,  "width": 140, "default": False},
    {"key": "maskavimas",           "label": "Maskavimas",           "type": "text",   "filter": "text",  "searchable": True,  "width": 150, "default": False},
    {"key": "atlikimo_terminas",    "label": "Atlikimo terminas",    "type": "date",   "filter": "date",  "searchable": False, "width": 150, "default": False},
    {"key": "testai_kokybe",        "label": "Testai/Kokybė",        "type": "text",   "filter": "text",  "searchable": True,  "width": 170, "default": False},

    # ===========================
    # [Pakavimas]
    # ===========================
    {"key": "pakavimas",            "label": "Pakavimas",              "type": "text",   "filter": "text",  "searchable": True,  "width": 140, "default": False},
    {"key": "instrukcija",          "label": "Instrukcija",            "type": "text",   "filter": "text",  "searchable": True,  "width": 160, "default": False},
    {"key": "pakavimo_dienos_norma","label": "Pakavimo dienos norma",  "type": "number", "filter": "range", "searchable": False, "width": 170, "default": False},
    {"key": "pak_po_ktl",           "label": "Pak. po KTL",            "type": "number", "filter": "range", "searchable": False, "width": 130, "default": False},
    {"key": "pak_po_milt",          "label": "Pak. po milt",           "type": "number", "filter": "range", "searchable": False, "width": 130, "default": False},

    # ===========================
    # [Kaina]
    # ===========================
    # Rodome tik galutinę, aktualią kainą. Visa kaina istorija bus kortelėje/peržiūroje.
    {"key": "kaina_eur", "label": "Kaina", "type": "number", "filter": "range", "searchable": False, "width": 120, "default": False},

    # ===========================
    # [Dokumentai]
    # ===========================
    {"key": "dok_count", "label": "Dokumentai", "type": "virtual", "filter": None, "searchable": False, "width": 120, "default": False},
    {"key": "pastabos",  "label": "Pastabos",   "type": "text",    "filter": "text", "searchable": True, "width": 220, "default": False},
]
