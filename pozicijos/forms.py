# pozicijos/forms.py
from __future__ import annotations

from django import forms
from django.forms import modelformset_factory

from .models import Pozicija, PozicijosBrezinys, MaskavimoEilute


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

            # Matmenys (mm) - NAUJA
            "x_mm",
            "y_mm",
            "z_mm",

            "kabinimo_budas",
            "kabinimas_reme",
            "detaliu_kiekis_reme",
            "faktinis_kiekis_reme",
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
            "maskavimo_tipas",
            "maskavimas",  # legacy / optional (nebenaudojam kaip privalomo)
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
            "padengimo_storis_um": forms.NumberInput(attrs={
                "min": 0,
                "step": "0.01",
                "inputmode": "decimal",
                "placeholder": "pvz. 80",
            }),
            "maskavimas": forms.Textarea(attrs={"rows": 2, "data-autoresize": "1"}),
            "instrukcija": forms.Textarea(attrs={"rows": 2, "data-autoresize": "1"}),
            "paslaugu_pastabos": forms.Textarea(attrs={"rows": 2, "data-autoresize": "1"}),
            "papildomos_paslaugos_aprasymas": forms.Textarea(attrs={"rows": 2, "data-autoresize": "1"}),
            "pastabos": forms.Textarea(attrs={"rows": 3, "data-autoresize": "1"}),

            # Matmenys (mm) - NAUJA
            "x_mm": forms.NumberInput(attrs={"min": 0, "step": "0.01", "inputmode": "decimal", "placeholder": "mm"}),
            "y_mm": forms.NumberInput(attrs={"min": 0, "step": "0.01", "inputmode": "decimal", "placeholder": "mm"}),
            "z_mm": forms.NumberInput(attrs={"min": 0, "step": "0.01", "inputmode": "decimal", "placeholder": "mm"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        if not getattr(self.instance, "pk", None):
            if "maskavimo_tipas" in self.fields:
                self.fields["maskavimo_tipas"].initial = "nera"
            if "papildomos_paslaugos" in self.fields:
                self.fields["papildomos_paslaugos"].initial = "ne"

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
        # Jei "nera" – išvalom; jei "yra" – paliekam optional tekstą.
        if tipas == "nera":
            cleaned["maskavimas"] = ""
        else:
            cleaned["maskavimas"] = apr

        # --- Paslaugos logika: KTL / Miltai / Paruošimas ---
        ktl = bool(cleaned.get("paslauga_ktl"))
        miltai = bool(cleaned.get("paslauga_miltai"))
        par = bool(cleaned.get("paslauga_paruosimas"))

        if ktl and miltai:
            self.add_error("paslauga_ktl", "Negalima pasirinkti kartu su „Miltai“.")
            self.add_error("paslauga_miltai", "Negalima pasirinkti kartu su „KTL“.")

        if ktl or miltai:
            cleaned["paslauga_paruosimas"] = True
            par = True

        if par and (not ktl) and (not miltai):
            if not (cleaned.get("paruosimas") or "").strip():
                cleaned["paruosimas"] = "Gardobond 24T"

        if ktl and not miltai:
            cleaned["padengimas"] = "KTL BASF CG 570"
            cleaned["padengimo_standartas"] = ""
            cleaned["spalva"] = "Juoda RAL 9005"

        if miltai and not ktl:
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
