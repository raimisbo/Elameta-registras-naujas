# pozicijos/forms_kainos.py
from __future__ import annotations

from django import forms
from django.forms import inlineformset_factory

from .models import Pozicija, KainosEilute


BUSENA_UI_CHOICES = [
    ("aktuali", "Aktuali"),
    ("neaktuali", "Neaktuali"),
]

MATAS_CHOICES = [
    ("vnt", "Vnt."),
    ("kg", "kg."),
    ("komplektas", "komplektas"),
]


class KainosEiluteForm(forms.ModelForm):
    """
    Vienos kainos eilutės forma pozicijos formsete.

    Pokyčiai:
    - Nebenaudojam UI lygmenyje "Fiksuota" / "Fx" (paliekam DB suderinamumui, bet nevaldoma per formą).
    - Matas = ChoiceField: Vnt. / kg. / komplektas (su fallback, jei DB turi kitą reikšmę).
    - Pastaba = textarea su auto-resize atributu (JS šablone).
    """

    busena_ui = forms.ChoiceField(
        label="Būsena",
        choices=BUSENA_UI_CHOICES,
        required=True,
    )

    # perrašom matas į ChoiceField (DB vis tiek CharField)
    matas = forms.ChoiceField(
        label="Matas",
        choices=MATAS_CHOICES,
        required=False,
    )

    class Meta:
        model = KainosEilute
        fields = [
            "kaina",
            "matas",
            "kiekis_nuo",
            "kiekis_iki",
            "galioja_nuo",
            "galioja_iki",
            "pastaba",
            # DB "busena" tiesiogiai nerodom – naudojam busena_ui
            # DB "yra_fiksuota" ir "fiksuotas_kiekis" sąmoningai NENAUDOJAMI UI.
        ]
        widgets = {
            "galioja_nuo": forms.DateInput(attrs={"type": "date"}),
            "galioja_iki": forms.DateInput(attrs={"type": "date"}),
            "pastaba": forms.Textarea(attrs={"rows": 1, "data-autoresize": "1"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # bendros klasės
        for name, f in self.fields.items():
            css = f.widget.attrs.get("class", "")
            f.widget.attrs["class"] = (css + " poz-field").strip()

        # kaina – decimal klaviatūra
        if "kaina" in self.fields:
            w = self.fields["kaina"].widget
            w.input_type = "text"
            w.attrs.setdefault("inputmode", "decimal")
            w.attrs.setdefault("placeholder", "0")

        # kiekiai – numeric klaviatūra
        for n in ("kiekis_nuo", "kiekis_iki"):
            if n in self.fields:
                w = self.fields[n].widget
                w.input_type = "text"
                w.attrs.setdefault("inputmode", "numeric")
                w.attrs.setdefault("placeholder", "")

        # Būsena UI init iš DB
        db_busena = getattr(self.instance, "busena", None) or "aktuali"
        self.fields["busena_ui"].initial = "aktuali" if db_busena == "aktuali" else "neaktuali"

        # MATAS fallback: jei DB turi kitą reikšmę, įtraukiam ją į choices, kad nelūžtų redagavimas
        current_matas = (getattr(self.instance, "matas", None) or "").strip()
        if current_matas:
            allowed_values = {v for v, _ in MATAS_CHOICES}
            if current_matas not in allowed_values:
                self.fields["matas"].choices = MATAS_CHOICES + [(current_matas, current_matas)]

    def clean(self):
        cleaned = super().clean()

        # UI -> DB busena
        bus_ui = cleaned.get("busena_ui") or "aktuali"
        cleaned["busena"] = "aktuali" if bus_ui == "aktuali" else "sena"

        # Leisti "bazinę" kainą be Nuo/Iki (jei reikia) – todėl Nuo/Iki nėra privalomi.
        # Jei norėsi griežčiau (reikalauti bent vieno), pasakyk – padarysim.
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
