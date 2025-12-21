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
    ("Vnt.", "Vnt."),
    ("kg", "kg"),
    ("komplektas", "komplektas"),
]


class KainosEiluteForm(forms.ModelForm):
    """
    Intervalinė kainodara (be fiksuotos kainos UI):

    - UI: Būsena = Aktuali / Neaktuali (Neaktuali -> DB "sena")
    - Privaloma: Kiekis nuo IR Kiekis iki (kai eilutė realiai pildoma)
    - Matas: Vnt. / kg / komplektas

    Svarbu: naujai pridėtai (bet paliktai tuščiai) eilutei naršyklė parenka matas=Vnt.
    Jeigu serverio initial būna None, Django laiko, kad forma "pasikeitė" ir pradeda validuoti,
    tada clean() priverstinai meta klaidas už Nuo/Iki. Todėl privalom suderinti initial su UI default.
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
            "kiekis_nuo",
            "kiekis_iki",
            "galioja_nuo",
            "galioja_iki",
            "pastaba",
        ]
        widgets = {
            "galioja_nuo": forms.DateInput(attrs={"type": "date"}),
            "galioja_iki": forms.DateInput(attrs={"type": "date"}),
            "pastaba": forms.Textarea(attrs={"rows": 1, "data-autoresize": "1"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # bendros klasės
        for _, f in self.fields.items():
            css = f.widget.attrs.get("class", "")
            f.widget.attrs["class"] = (css + " poz-field").strip()

        # matas = select su ribotais pasirinkimais
        if "matas" in self.fields:
            self.fields["matas"].required = True
            self.fields["matas"].widget = forms.Select(choices=MATAS_CHOICES)

            # UŽDĖT INITIAL:
            # - esamai eilutei: iš instancijos
            # - naujai (empty_form): sutampa su naršyklės default (pirma reikšmė = "Vnt.")
            default_matas = MATAS_CHOICES[0][0] if MATAS_CHOICES else None
            inst_matas = getattr(self.instance, "matas", None)
            self.fields["matas"].initial = inst_matas or default_matas

        # skaitiniai – patogesni input'ai
        if "kaina" in self.fields:
            w = self.fields["kaina"].widget
            w.input_type = "text"
            w.attrs.setdefault("inputmode", "decimal")
            w.attrs.setdefault("placeholder", "0")

        for n in ("kiekis_nuo", "kiekis_iki"):
            if n in self.fields:
                w = self.fields[n].widget
                w.input_type = "text"
                w.attrs.setdefault("inputmode", "numeric")
                w.attrs.setdefault("placeholder", "")

        # inicializuojam busena_ui iš DB (empty_form -> bus "aktuali", kas ir ok)
        db_busena = getattr(self.instance, "busena", None) or "aktuali"
        self.fields["busena_ui"].initial = "aktuali" if db_busena == "aktuali" else "neaktuali"

    def clean(self):
        cleaned = super().clean()

        # UI -> DB busena
        bus_ui = cleaned.get("busena_ui") or "aktuali"
        cleaned["busena"] = "aktuali" if bus_ui == "aktuali" else "sena"

        kn = cleaned.get("kiekis_nuo")
        kk = cleaned.get("kiekis_iki")

        # PRIVALOMA: abu (kai forma realiai validuojama)
        if kn in (None, ""):
            self.add_error("kiekis_nuo", "Privaloma užpildyti „Kiekis nuo“.")
        if kk in (None, ""):
            self.add_error("kiekis_iki", "Privaloma užpildyti „Kiekis iki“.")

        # jei abu yra – logika
        try:
            if kn is not None and kk is not None and str(kn).strip() != "" and str(kk).strip() != "":
                if int(kn) > int(kk):
                    self.add_error("kiekis_iki", "„Kiekis iki“ turi būti didesnis arba lygus „Kiekis nuo“.")
        except Exception:
            # jei vartotojas įvedė ne skaičių – Django pats paprastai duoda klaidą
            pass

        return cleaned

    def save(self, commit=True):
        inst: KainosEilute = super().save(commit=False)

        # busena_ui -> inst.busena
        bus_ui = self.cleaned_data.get("busena_ui") or "aktuali"
        inst.busena = "aktuali" if bus_ui == "aktuali" else "sena"

        # kad neliktų fiksuotos logikos DB lygyje (UI jos nebėra)
        if hasattr(inst, "yra_fiksuota"):
            inst.yra_fiksuota = False
        if hasattr(inst, "fiksuotas_kiekis"):
            inst.fiksuotas_kiekis = None

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
