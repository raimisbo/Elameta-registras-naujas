# pozicijos/forms_kainos.py
from __future__ import annotations

from django import forms
from django.forms import inlineformset_factory

from .models import Pozicija, KainosEilute


# UI rodome tik 2 būsenas, bet DB turi: "aktuali", "sena", "pasiulymas"
# Mes pasirenkam: Neaktuali -> "sena"
BUSENA_UI_CHOICES = [
    ("aktuali", "Aktuali"),
    ("neaktuali", "Neaktuali"),
]


class KainosEiluteForm(forms.ModelForm):
    """
    Vienos kainos eilutės forma pozicijos formsete.

    - UI: busena tik "Aktuali" / "Neaktuali"
    - DB: "Neaktuali" map'inama į "sena"
    """

    busena_ui = forms.ChoiceField(
        label="Būsena",
        choices=BUSENA_UI_CHOICES,
        required=True,
    )

    class Meta:
        model = KainosEilute
        fields = [
            "kaina",
            "matas",
            "yra_fiksuota",
            "kiekis_nuo",
            "kiekis_iki",
            "fiksuotas_kiekis",
            "galioja_nuo",
            "galioja_iki",
            "pastaba",
            # busena DB lauko tiesiogiai nerodom – naudojam busena_ui
        ]
        widgets = {
            "galioja_nuo": forms.DateInput(format="%Y-%m-%d", attrs={"placeholder": "YYYY-MM-DD"}),
            "galioja_iki": forms.DateInput(format="%Y-%m-%d", attrs={"placeholder": "YYYY-MM-DD"}),
            "pastaba": forms.Textarea(attrs={"rows": 2}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # bendros klasės
        for name, f in self.fields.items():
            css = f.widget.attrs.get("class", "")
            f.widget.attrs["class"] = (css + " poz-field").strip()

        # skaitiniai – be rodyklių, bet su decimal klaviatūra
        if "kaina" in self.fields:
            w = self.fields["kaina"].widget
            w.input_type = "text"
            w.attrs.setdefault("inputmode", "decimal")
            w.attrs.setdefault("placeholder", "0")

        for n in ("kiekis_nuo", "kiekis_iki", "fiksuotas_kiekis"):
            if n in self.fields:
                w = self.fields[n].widget
                w.input_type = "text"
                w.attrs.setdefault("inputmode", "numeric")
                w.attrs.setdefault("placeholder", "")

        # Inicializuojam busena_ui iš DB busena
        db_busena = getattr(self.instance, "busena", None) or "aktuali"
        self.fields["busena_ui"].initial = "aktuali" if db_busena == "aktuali" else "neaktuali"

    def clean(self):
        cleaned = super().clean()

        yra_fiksuota = cleaned.get("yra_fiksuota")
        fiksuotas_kiekis = cleaned.get("fiksuotas_kiekis")
        kiekis_nuo = cleaned.get("kiekis_nuo")
        kiekis_iki = cleaned.get("kiekis_iki")

        # UI -> DB busena
        bus_ui = cleaned.get("busena_ui") or "aktuali"
        cleaned["busena"] = "aktuali" if bus_ui == "aktuali" else "sena"

        # Validacija pagal tavo modelio KainosEilute.clean logiką
        if yra_fiksuota:
            if fiksuotas_kiekis in (None, ""):
                self.add_error("fiksuotas_kiekis", "Fiksuotai kainai privalomas „Fiksuotas kiekis“.")
            if kiekis_nuo not in (None, "") or kiekis_iki not in (None, ""):
                self.add_error("kiekis_nuo", "Fiksuotai kainai „Kiekis nuo/iki“ turi būti tušti.")
                self.add_error("kiekis_iki", "Fiksuotai kainai „Kiekis nuo/iki“ turi būti tušti.")
        else:
            if (kiekis_nuo in (None, "") and kiekis_iki in (None, "")):
                self.add_error("kiekis_nuo", "Intervalinei kainai užpildykite bent „Kiekis nuo“ arba „Kiekis iki“.")

        return cleaned

    def save(self, commit=True):
        inst: KainosEilute = super().save(commit=False)

        # busena_ui -> inst.busena
        bus_ui = self.cleaned_data.get("busena_ui") or "aktuali"
        inst.busena = "aktuali" if bus_ui == "aktuali" else "sena"

        if commit:
            inst.save()
        return inst


KainaFormSet = inlineformset_factory(
    Pozicija,
    KainosEilute,
    form=KainosEiluteForm,
    extra=0,
    can_delete=True,
)
