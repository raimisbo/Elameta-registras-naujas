"""
Visų pozicijų sąrašo stulpelių schema.

- key:    modelio laukas arba property
- label:  stulpelio pavadinimas
- type:   "char" | "number" | "date" | "virtual"
- filter: "text" | "range" | "date" | None
- searchable: ar dalyvauja globalioje q paieškoje
- width:  numanomam stulpelio pločiui (px)
- default: ar rodomas pagal nutylėjimą
"""

COLUMNS: list[dict] = [
    # ---------------- Pagrindinė info ----------------
    {
        "key": "klientas",
        "label": "Klientas",
        "type": "char",
        "filter": "text",
        "searchable": True,
        "width": 180,
        "default": True,
    },
    {
        "key": "projektas",
        "label": "Projektas",
        "type": "char",
        "filter": "text",
        "searchable": True,
        "width": 160,
        "default": True,
    },
    {
        "key": "poz_kodas",
        "label": "Pozicijos kodas",
        "type": "char",
        "filter": "text",
        "searchable": True,
        "width": 150,
        "default": True,
    },
    {
        "key": "poz_pavad",
        "label": "Pozicijos pavadinimas",
        "type": "char",
        "filter": "text",
        "searchable": True,
        "width": 260,
        "default": True,
    },

    # ---------------- Specifikacija ----------------
    {
        "key": "metalas",
        "label": "Metalas",
        "type": "char",
        "filter": "text",
        "searchable": False,
        "width": 120,
        "default": True,
    },
    {
        "key": "plotas",
        "label": "Plotas",
        "type": "number",
        "filter": "range",
        "searchable": False,
        "width": 90,
        "default": False,
        "align": "right",
    },
    {
        "key": "svoris",
        "label": "Svoris",
        "type": "number",
        "filter": "range",
        "searchable": False,
        "width": 90,
        "default": False,
        "align": "right",
    },

    # ---------------- Kabinimas ----------------
    {
        "key": "kabinimo_budas",
        "label": "Kabinimo būdas",
        "type": "char",
        "filter": "text",
        "searchable": False,
        "width": 140,
        "default": False,
    },
    {
        "key": "kabinimas_reme",
        "label": "Kabinimas rėme",
        "type": "char",
        "filter": "text",
        "searchable": False,
        "width": 140,
        "default": False,
    },
    {
        "key": "detaliu_kiekis_reme",
        "label": "Detalių kiekis rėme",
        "type": "number",
        "filter": "range",
        "searchable": False,
        "width": 110,
        "default": False,
        "align": "right",
    },
    {
        "key": "faktinis_kiekis_reme",
        "label": "Faktinis kiekis rėme",
        "type": "number",
        "filter": "range",
        "searchable": False,
        "width": 120,
        "default": False,
        "align": "right",
    },

    # ---------------- Paslauga (paviršius / dažymas) ----------------
    {
        "key": "paruosimas",
        "label": "Paruošimas",
        "type": "char",
        "filter": "text",
        "searchable": False,
        "width": 140,
        "default": False,
    },
    {
        "key": "padengimas",
        "label": "Padengimas",
        "type": "char",
        "filter": "text",
        "searchable": False,
        "width": 140,
        "default": True,
    },
    {
        "key": "padengimo_standartas",
        "label": "Padengimo standartas",
        "type": "char",
        "filter": "text",
        "searchable": False,
        "width": 160,
        "default": False,
    },
    {
        "key": "spalva",
        "label": "Spalva",
        "type": "char",
        "filter": "text",
        "searchable": False,
        "width": 120,
        "default": False,
    },

    # ---------------- Maskavimas ----------------
    {
        "key": "maskavimo_tipas",
        "label": "Maskavimas",
        "type": "char",
        "filter": "text",
        "searchable": False,
        "width": 140,
        "default": False,
    },

    # ---------------- Kiti techniniai ----------------
    {
        "key": "testai_kokybe",
        "label": "Testai / kokybė",
        "type": "char",
        "filter": "text",
        "searchable": False,
        "width": 180,
        "default": False,
    },
    {
        # buvo date -> dabar darbo dienų skaičius
        "key": "atlikimo_terminas",
        "label": "Atlikimo terminas (d.d.)",
        "type": "number",
        "filter": "range",
        "searchable": False,
        "width": 140,
        "default": False,
        "align": "right",
    },

    # ---------------- Pakavimas ----------------
    {
        "key": "pakavimo_tipas",
        "label": "Pakavimas",
        "type": "char",
        "filter": "text",
        "searchable": False,
        "width": 140,
        "default": False,
    },

    # ---------------- Kaina / pastabos ----------------
    {
        "key": "kaina_eur",
        "label": "Kaina, EUR",
        "type": "number",
        "filter": "range",
        "searchable": False,
        "width": 100,
        "default": True,
        "align": "right",
    },
    {
        "key": "pastabos",
        "label": "Pastabos",
        "type": "char",
        "filter": "text",
        "searchable": False,
        "width": 260,
        "default": False,
    },

    # ---------------- Sisteminiai ----------------
    {
        "key": "created",
        "label": "Sukurta",
        "type": "date",
        "filter": "date",
        "searchable": False,
        "width": 120,
        "default": False,
    },
    {
        "key": "updated",
        "label": "Atnaujinta",
        "type": "date",
        "filter": "date",
        "searchable": False,
        "width": 120,
        "default": False,
    },

    # ---------------- Virtualūs laukai ----------------
    {
        "key": "brez_count",
        "label": "Brėžiniai",
        "type": "virtual",
        "filter": None,
        "searchable": False,
        "width": 90,
        "default": False,
    },
    {
        "key": "dok_count",
        "label": "Dokumentai",
        "type": "virtual",
        "filter": None,
        "searchable": False,
        "width": 100,
        "default": False,
    },
]
