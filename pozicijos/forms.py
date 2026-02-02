# pozicijos/forms.py
from __future__ import annotations

import re
from decimal import Decimal, InvalidOperation
from django import forms
from django.forms import modelformset_factory

from .models import Pozicija, PozicijosBrezinys, MaskavimoEilute

# KTL kabinimo būdo pasirinkimai (tik UI widgetui)
KTL_KABINIMO_CHOICES = [
    ("", "—"),
    ("girliandos", "Girliandos"),
    ("traversas", "Traversas"),
    ("pakabos", "Pakabos"),
    ("specialus", "Specialus"),
]

_RE_NUM = re.compile(r"^\d+(?:[.,]\d+)?$")
_RE_RANGE = re.compile(r"^\d+(?:[.,]\d+)?\s*(?:-|\.\.)\s*\d+(?:[.,]\d+)?$")
_RE_CMP = re.compile(r"^(>=|<=|>|<)\s*\d+(?:[.,]\d+)?$")


def _norm_thickness(value: str) -> str:
    s = (value or "").strip()
    if not s:
        return ""

    # brūkšniai -> '-'
    s = s.replace("–", "-").replace("—", "-")
    # '..' -> '-'
    s = re.sub(r"\.\.\s*", "-", s)

    # tarpai
    s = re.sub(r"\s+", " ", s).strip()

    # kablelis -> taškas
    s = s.replace(",", ".")

    # tarpai aplink '-'
    s = re.sub(r"\s*-\s*", "-", s)

    # tarpai po operatorių (>=, <=, >, <)
    s = re.sub(r"^(>=|<=|>|<)\s*", r"\1", s)

    return s


def _parse_num(s: str) -> float:
    return float((s or "").replace(",", "."))


class PozicijaForm(forms.ModelForm):
    KTL_KABINIMO_CHOICES = [
        ("", "—"),
        ("Girliandos", "Girliandos"),
        ("Traversas", "Traversas"),
        ("Pakabos", "Pakabos"),
        ("Specialus", "Specialus"),
    ]

    class Meta:
        model = Pozicija
        fields = [
            # Pagrindiniai
            "klientas",
            "projektas",
            "poz_kodas",
            "poz_pavad",

            # Detalė
            "metalas",
            "metalo_storis",
            "plotas",
            "svoris",
            "x_mm",
            "y_mm",
            "z_mm",

            # Paslaugos (bendras blokas)
            "paslauga_ktl",
            "paslauga_miltai",
            "paslauga_paruosimas",
            "paruosimas",
            "padengimas",
            "padengimo_standartas",

            "partiju_dydziai",
            "metinis_kiekis_nuo",
            "metinis_kiekis_iki",
            "projekto_gyvavimo_nuo",
            "projekto_gyvavimo_iki",
            # Spalva – legacy (UI nerodom; sinchronizuojam su Miltų spalva)
            "spalva",

            # KTL sub-blokas
            "ktl_kabinimo_budas",
            "ktl_kabinimas_reme_txt",
            "ktl_detaliu_kiekis_reme",
            "ktl_faktinis_kiekis_reme",
            "ktl_ilgis_mm",
            "ktl_aukstis_mm",
            "ktl_gylis_mm",
            "ktl_kabinimas_aprasymas",
            "ktl_dangos_storis_um",
            "ktl_pastabos",

            # Miltai sub-blokas
            "miltu_kodas",
            "miltu_spalva",
            "miltu_tiekejas",
            "miltu_blizgumas",
            "miltu_kaina",
            "miltai_kiekis_per_valanda",
            "miltai_faktinis_per_valanda",
            "miltai_detaliu_kiekis_reme",
            "miltai_faktinis_kiekis_reme",
            "miltai_kabinimas_aprasymas",
            "miltai_dangos_storis_um",
            "miltai_pastabos",

            # Bendros paslaugų pastabos
            "paslaugu_pastabos",

            # Terminai / Kokybė / Pakavimas / Papildomos / Pastabos
            "atlikimo_terminas",
            "testai_kokybe",

            "pakavimo_tipas",
            "pakavimas",
            "instrukcija",

            "papildomos_paslaugos",
            "papildomos_paslaugos_aprasymas",

            "pastabos",
        ]

        labels = {
            "pakavimas": "Aprašymas",
            "instrukcija": "Pastabos",
        }

        widgets = {
            "atlikimo_terminas": forms.NumberInput(attrs={"min": 0, "step": 1, "inputmode": "numeric"}),

            "metalo_storis": forms.NumberInput(attrs={"min": 0, "step": "0.01", "inputmode": "decimal", "placeholder": "mm"}),

            "instrukcija": forms.Textarea(attrs={"rows": 2, "data-autoresize": "1"}),
            "paslaugu_pastabos": forms.Textarea(attrs={"rows": 2, "data-autoresize": "1"}),
            "papildomos_paslaugos_aprasymas": forms.Textarea(attrs={"rows": 2, "data-autoresize": "1"}),
            "pastabos": forms.Textarea(attrs={"rows": 3, "data-autoresize": "1"}),

            # Matmenys XYZ (mm)
            "x_mm": forms.NumberInput(attrs={"min": 0, "step": "0.01", "inputmode": "decimal", "placeholder": "mm"}),
            "y_mm": forms.NumberInput(attrs={"min": 0, "step": "0.01", "inputmode": "decimal", "placeholder": "mm"}),
            "z_mm": forms.NumberInput(attrs={"min": 0, "step": "0.01", "inputmode": "decimal", "placeholder": "mm"}),

            # KTL
            "ktl_kabinimo_budas": forms.Select(choices=KTL_KABINIMO_CHOICES),
            "ktl_kabinimas_reme_txt": forms.TextInput(attrs={"placeholder": "įrašysite ranka"}),
            "ktl_detaliu_kiekis_reme": forms.NumberInput(attrs={"min": 0, "step": 1, "inputmode": "numeric"}),
            "ktl_faktinis_kiekis_reme": forms.NumberInput(attrs={"min": 0, "step": 1, "inputmode": "numeric"}),

            # I / A / G (be mm UI'e)
            "ktl_ilgis_mm": forms.NumberInput(attrs={"min": 0, "step": "0.1", "inputmode": "decimal", "data-decimals": "1"}),
            "ktl_aukstis_mm": forms.NumberInput(attrs={"min": 0, "step": "0.1", "inputmode": "decimal", "data-decimals": "1"}),
            "ktl_gylis_mm": forms.NumberInput(attrs={"min": 0, "step": "0.1", "inputmode": "decimal", "data-decimals": "1"}),

            "ktl_kabinimas_aprasymas": forms.Textarea(attrs={"rows": 2, "data-autoresize": "1"}),
            "ktl_dangos_storis_um": forms.NumberInput(attrs={"min": 0, "step": "0.1", "inputmode": "decimal", "data-decimals": "1"}),
            "ktl_pastabos": forms.Textarea(attrs={"rows": 2, "data-autoresize": "1"}),

            # Miltai
            "miltu_kaina": forms.NumberInput(attrs={"min": 0, "step": "0.0001", "inputmode": "decimal", "data-decimals": "4"}),

            "miltai_kiekis_per_valanda": forms.NumberInput(attrs={"min": 0, "step": "0.1", "inputmode": "decimal", "data-decimals": "1"}),
            "miltai_faktinis_per_valanda": forms.NumberInput(attrs={"min": 0, "step": "0.1", "inputmode": "decimal", "data-decimals": "1"}),
            "miltai_detaliu_kiekis_reme": forms.NumberInput(attrs={"min": 0, "step": 1, "inputmode": "numeric"}),
            "miltai_faktinis_kiekis_reme": forms.NumberInput(attrs={"min": 0, "step": 1, "inputmode": "numeric"}),
            "miltai_kabinimas_aprasymas": forms.Textarea(attrs={"rows": 2, "data-autoresize": "1"}),

            "miltai_dangos_storis_um": forms.NumberInput(attrs={"min": 0, "step": "0.1", "inputmode": "decimal", "data-decimals": "1"}),
            "miltai_pastabos": forms.Textarea(attrs={"rows": 2, "data-autoresize": "1"}),
            "partiju_dydziai": forms.TextInput(attrs={"placeholder": "pvz. 50, 100, 250"}),
            "metinis_kiekis_nuo": forms.NumberInput(attrs={"min": 0}),
            "metinis_kiekis_iki": forms.NumberInput(attrs={"min": 0}),
            "projekto_gyvavimo_nuo": forms.DateInput(attrs={"type": "date"}),
            "projekto_gyvavimo_iki": forms.DateInput(attrs={"type": "date"}),

        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # UI: I/A/G be "mm" (DB laukai tie patys – nekeičiam struktūros)
        if "ktl_ilgis_mm" in self.fields:
            self.fields["ktl_ilgis_mm"].label = "I"
            self.fields["ktl_aukstis_mm"].label = "A"
            self.fields["ktl_gylis_mm"].label = "G"

        if not getattr(self.instance, "pk", None):
            if "papildomos_paslaugos" in self.fields:
                self.fields["papildomos_paslaugos"].initial = "ne"

    def clean(self):
        cleaned = super().clean()

        # --- Metalo storis (mm): leidžiam kablelį, 2 sk. po kablelio ---
        metalo_storis_raw = (self.data.get("metalo_storis") or "").strip()
        if metalo_storis_raw:
            try:
                cleaned["metalo_storis"] = Decimal(metalo_storis_raw.replace(",", ".")).quantize(Decimal("0.01"))
            except (InvalidOperation, ValueError):
                self.add_error("metalo_storis", "Įveskite skaičių (mm), pvz. 1.50")


        # --- Paslaugos logika: KTL / Miltai / Paruošimas ---
        ktl = bool(cleaned.get("paslauga_ktl"))
        miltai = bool(cleaned.get("paslauga_miltai"))
        par = bool(cleaned.get("paslauga_paruosimas"))

        # A1: jei yra KTL arba Miltai – Paruošimas privalomas
        if ktl or miltai:
            cleaned["paslauga_paruosimas"] = True
            par = True

        def _is_empty(v):
            return not (v or "").strip()

        # jei Paruošimas vienas pats – default tik jei tuščia
        if par and (not ktl) and (not miltai):
            if _is_empty(cleaned.get("paruosimas", "")):
                cleaned["paruosimas"] = "Gardobond 24T"

        # KTL presetai (pildom tik tuščius)
        if ktl:
            if _is_empty(cleaned.get("padengimas", "")):
                cleaned["padengimas"] = "KTL BASF CG 570"
            if cleaned.get("padengimo_standartas", None) is None:
                cleaned["padengimo_standartas"] = ""

        # Spalva tik Miltams: legacy laukas spalva sinchronizuojamas su miltu_spalva
        miltu_sp = (cleaned.get("miltu_spalva") or "").strip()
        if miltai:
            if miltu_sp:
                cleaned["spalva"] = miltu_sp
        else:
            cleaned["spalva"] = ""

        # --- Papildomos paslaugos ---
        pp = (cleaned.get("papildomos_paslaugos") or "ne").strip().lower()
        pp_txt = (cleaned.get("papildomos_paslaugos_aprasymas") or "").strip()

        if pp not in ("ne", "taip"):
            pp = "ne"
        cleaned["papildomos_paslaugos"] = pp

        if pp == "ne":
            cleaned["papildomos_paslaugos_aprasymas"] = ""
        else:
            if not pp_txt:
                self.add_error("papildomos_paslaugos_aprasymas", "Kai pasirinkta „Taip“, aprašymas yra privalomas.")
        # --- Paslauga: metiniai kiekiai (nuo/iki) ---
        mk_nuo = cleaned.get("metinis_kiekis_nuo")
        mk_iki = cleaned.get("metinis_kiekis_iki")
        if mk_nuo is not None and mk_iki is not None and mk_nuo > mk_iki:
            self.add_error("metinis_kiekis_nuo", "„Nuo“ negali būti didesnis už „Iki“.")
            self.add_error("metinis_kiekis_iki", "„Iki“ negali būti mažesnis už „Nuo“.")

        # --- Paslauga: projekto gyvavimo laikotarpis (nuo/iki) ---
        pg_nuo = cleaned.get("projekto_gyvavimo_nuo")
        pg_iki = cleaned.get("projekto_gyvavimo_iki")
        if pg_nuo and pg_iki and pg_nuo > pg_iki:
            self.add_error("projekto_gyvavimo_nuo", "„Nuo“ negali būti vėliau už „Iki“.")
            self.add_error("projekto_gyvavimo_iki", "„Iki“ negali būti anksčiau už „Nuo“.")


        return cleaned


class PozicijosBrezinysForm(forms.ModelForm):
    class Meta:
        model = PozicijosBrezinys
        fields = ["failas", "pavadinimas"]
        widgets = {
            "pavadinimas": forms.TextInput(attrs={"placeholder": "Pavadinimas"}),
        }


# --- Maskavimo eilutės (formset) ---

class MaskavimoEiluteForm(forms.ModelForm):
    class Meta:
        model = MaskavimoEilute
        fields = ["maskuote", "vietu_kiekis", "aprasymas"]
        widgets = {
            "maskuote": forms.TextInput(attrs={"placeholder": "Maskuotė"}),
            "vietu_kiekis": forms.NumberInput(attrs={"min": 0, "step": 1, "inputmode": "numeric", "placeholder": "Kiekis"}),
            "aprasymas": forms.Textarea(attrs={"rows": 2, "data-autoresize": "1", "placeholder": "Aprašymas"}),
        }


MaskavimoFormSet = modelformset_factory(
    MaskavimoEilute,
    form=MaskavimoEiluteForm,
    extra=0,
    can_delete=True,
)