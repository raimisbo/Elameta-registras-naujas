from __future__ import annotations

from django import forms

from .models import Pozicija, PozicijosBrezinys


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
            "kabinimo_budas",
            "kabinimas_reme",
            "detaliu_kiekis_reme",
            "faktinis_kiekis_reme",
            "paruosimas",
            "padengimas",
            "padengimo_standartas",
            "spalva",
            "paslauga_ktl",
            "paslauga_miltai",
            "paslauga_paruosimas",
            "miltu_kodas",
            "miltu_spalva",
            "miltu_tiekejas",
            "miltu_blizgumas",
            "miltu_kaina",
            "maskavimo_tipas",
            "maskavimas",
            "atlikimo_terminas",
            "testai_kokybe",
            "pakavimo_tipas",
            "pakavimas",
            "instrukcija",
            "pastabos",
        ]
        widgets = {
            # atlikimo_terminas: darbo dienų skaičius
            "atlikimo_terminas": forms.NumberInput(attrs={"min": 0, "step": 1, "inputmode": "numeric"}),

            "maskavimas": forms.Textarea(attrs={"rows": 2, "data-autoresize": "1"}),
            "instrukcija": forms.Textarea(attrs={"rows": 2, "data-autoresize": "1"}),
            "pastabos": forms.Textarea(attrs={"rows": 3, "data-autoresize": "1"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # default naujam įrašui
        if not getattr(self.instance, "pk", None):
            if "maskavimo_tipas" in self.fields:
                self.fields["maskavimo_tipas"].initial = "nera"

    def clean(self):
        cleaned = super().clean()

        raw_tipas = (cleaned.get("maskavimo_tipas") or "").strip().lower()
        apr = (cleaned.get("maskavimas") or "").strip()

        # Normalizuojam viską į "nera" / "yra"
        if raw_tipas in ("ners", "nera", "", "none", "null"):
            tipas = "nera"
        elif raw_tipas in ("yra", "iprastas", "specialus"):
            tipas = "yra"
        else:
            tipas = "nera"

        cleaned["maskavimo_tipas"] = tipas

        if tipas == "nera":
            # Nėra -> aprašymas visada tuščias, ir NIEKADA neblokuojam
            cleaned["maskavimas"] = ""
        else:
            # Yra -> aprašymas privalomas
            if not apr:
                self.add_error("maskavimas", "Kai „Maskavimas = Yra“, aprašymas yra privalomas.")

        return cleaned


class PozicijosBrezinysForm(forms.ModelForm):
    class Meta:
        model = PozicijosBrezinys
        fields = ["failas", "pavadinimas"]
        widgets = {
            "pavadinimas": forms.TextInput(attrs={"placeholder": "Pavadinimas"}),
        }
