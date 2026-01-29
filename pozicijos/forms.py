# pozicijos/forms.py
from __future__ import annotations

import re
from django import forms
from django.forms import modelformset_factory

from .models import Pozicija, PozicijosBrezinys, MaskavimoEilute


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
    class Meta:
        model = Pozicija
        fields = [
            "klientas",
            "projektas",
            "poz_kodas",
            "poz_pavad",
            "metalas",
            "plotas",
            "svoris",

            # Matmenys (mm)
            "x_mm",
            "y_mm",
            "z_mm",

            # Legacy kabinimas (paliekam)

            # Kabinimas (KTL) - NAUJA
            "ktl_kabinimo_budas",
            "ktl_kabinimas_reme_txt",
            "ktl_detaliu_kiekis_reme",
            "ktl_faktinis_kiekis_reme",
            "ktl_ilgis_mm",
            "ktl_aukstis_mm",
            "ktl_gylis_mm",
            "ktl_kabinimas_aprasymas",

            # Kabinimas (Miltai) - NAUJA
            "miltai_kiekis_per_valanda",
            "miltai_detaliu_kiekis_reme",
            "miltai_faktinis_kiekis_reme",
            "miltai_kabinimas_aprasymas",

            # Paslaugos
            "paruosimas",
            "padengimas",
            "padengimo_standartas",
            "spalva",
            "padengimo_storis_um",
            "paslauga_ktl",
            "paslauga_miltai",
            "paslauga_paruosimas",

            "miltu_kodas",
            "miltu_spalva",
            "miltu_tiekejas",
            "miltu_blizgumas",
            "miltu_kaina",

            "paslaugu_pastabos",

            # Maskavimas
            "maskavimo_tipas",
            "maskavimas",  # legacy / optional

            "atlikimo_terminas",
            "testai_kokybe",

            # Pakavimas
            "pakavimo_tipas",
            "pakavimas",
            "instrukcija",

            # Papildomos
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

            # SVARBU: TextInput (ne number), kad leistų 60-80, >60, >=60 ir pan.
            "padengimo_storis_um": forms.TextInput(attrs={
                "inputmode": "decimal",
                "placeholder": "pvz. 80, 60-120, >60, >=60",
            }),

            "maskavimas": forms.Textarea(attrs={"rows": 2, "data-autoresize": "1"}),
            "instrukcija": forms.Textarea(attrs={"rows": 2, "data-autoresize": "1"}),
            "paslaugu_pastabos": forms.Textarea(attrs={"rows": 2, "data-autoresize": "1"}),
            "papildomos_paslaugos_aprasymas": forms.Textarea(attrs={"rows": 2, "data-autoresize": "1"}),
            "pastabos": forms.Textarea(attrs={"rows": 3, "data-autoresize": "1"}),

            # Matmenys (mm)
            "x_mm": forms.NumberInput(attrs={"min": 0, "step": "0.01", "inputmode": "decimal", "placeholder": "mm"}),
            "y_mm": forms.NumberInput(attrs={"min": 0, "step": "0.01", "inputmode": "decimal", "placeholder": "mm"}),
            "z_mm": forms.NumberInput(attrs={"min": 0, "step": "0.01", "inputmode": "decimal", "placeholder": "mm"}),

            # Kabinimas (KTL / Miltai) - NAUJA
            "ktl_kabinimo_budas": forms.TextInput(attrs={"placeholder": "laisvas tekstas"}),
            "ktl_kabinimas_reme_txt": forms.TextInput(attrs={"placeholder": "įrašysite ranka"}),
            "ktl_detaliu_kiekis_reme": forms.NumberInput(attrs={"min": 0, "step": 1, "inputmode": "numeric"}),
            "ktl_faktinis_kiekis_reme": forms.NumberInput(attrs={"min": 0, "step": 1, "inputmode": "numeric"}),

            "ktl_ilgis_mm": forms.NumberInput(attrs={"min": 0, "step": "0.1", "inputmode": "decimal", "placeholder": "mm", "data-decimals": "1"}),
            "ktl_aukstis_mm": forms.NumberInput(attrs={"min": 0, "step": "0.1", "inputmode": "decimal", "placeholder": "mm", "data-decimals": "1"}),
            "ktl_gylis_mm": forms.NumberInput(attrs={"min": 0, "step": "0.1", "inputmode": "decimal", "placeholder": "mm", "data-decimals": "1"}),

            "ktl_kabinimas_aprasymas": forms.Textarea(attrs={"rows": 2, "data-autoresize": "1"}),
            "miltai_kiekis_per_valanda": forms.NumberInput(attrs={"min": 0, "step": "0.1", "inputmode": "decimal", "data-decimals": "1"}),
            "miltai_detaliu_kiekis_reme": forms.NumberInput(attrs={"min": 0, "step": 1, "inputmode": "numeric"}),
            "miltai_faktinis_kiekis_reme": forms.NumberInput(attrs={"min": 0, "step": 1, "inputmode": "numeric"}),
            "miltai_kabinimas_aprasymas": forms.Textarea(attrs={"rows": 2, "data-autoresize": "1"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        if not getattr(self.instance, "pk", None):
            if "maskavimo_tipas" in self.fields:
                self.fields["maskavimo_tipas"].initial = "nera"
            if "papildomos_paslaugos" in self.fields:
                self.fields["papildomos_paslaugos"].initial = "ne"

    def clean_padengimo_storis_um(self):
        raw = self.cleaned_data.get("padengimo_storis_um", "")
        s = _norm_thickness(raw)
        if not s:
            return ""

        if _RE_NUM.match(s):
            return s

        if _RE_CMP.match(s):
            return s

        if _RE_RANGE.match(s):
            a, b = s.split("-", 1)
            try:
                fa = _parse_num(a)
                fb = _parse_num(b)
            except ValueError:
                raise forms.ValidationError("Neteisingas formatas. Pvz.: 70, 60-80, >60, >=60.")
            if fa > fb:
                raise forms.ValidationError("Rėžyje „nuo“ turi būti mažiau arba lygu „iki“.")
            return f"{a}-{b}"

        raise forms.ValidationError("Neteisingas formatas. Pvz.: 70, 60-80, >60, >=60, <80, <=80.")

    def clean(self):
        cleaned = super().clean()

        # --- Maskavimas ---
        raw_tipas = (cleaned.get("maskavimo_tipas") or "").strip().lower()
        apr = (cleaned.get("maskavimas") or "").strip()

        if raw_tipas in ("nera", "", "none", "null"):
            tipas = "nera"
        elif raw_tipas in ("yra",):
            tipas = "yra"
        else:
            tipas = "nera"

        cleaned["maskavimo_tipas"] = tipas

        # Legacy laukas: nebėra privalomas.
        if tipas == "nera":
            cleaned["maskavimas"] = ""
        else:
            cleaned["maskavimas"] = apr

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

        # B2: jei Paruošimas vienas pats – default tik jei tuščia
        if par and (not ktl) and (not miltai):
            if _is_empty(cleaned.get("paruosimas", "")):
                cleaned["paruosimas"] = "Gardobond 24T"

        # B2 + Variant B: KTL presetai (pildom tik tuščius)
        if ktl:
            if _is_empty(cleaned.get("padengimas", "")):
                cleaned["padengimas"] = "KTL BASF CG 570"
            if cleaned.get("padengimo_standartas", None) is None:
                cleaned["padengimo_standartas"] = ""
            if _is_empty(cleaned.get("spalva", "")):
                cleaned["spalva"] = "Juoda RAL 9005"

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
        fields = ["maskuote", "vietu_kiekis"]
        widgets = {
            "maskuote": forms.TextInput(attrs={"placeholder": "Maskuotė"}),
            "vietu_kiekis": forms.NumberInput(attrs={"min": 0, "step": 1, "inputmode": "numeric", "placeholder": "Kiekis"}),
        }


MaskavimoFormSet = modelformset_factory(
    MaskavimoEilute,
    form=MaskavimoEiluteForm,
    extra=0,
    can_delete=True,
)
