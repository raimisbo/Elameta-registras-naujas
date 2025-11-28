# pozicijos/forms.py
from django import forms
from django.forms import inlineformset_factory

from .models import Pozicija, PozicijosKaina, PozicijosBrezinys, KainosEilute
from .schemas.columns import COLUMNS


# Laukai, kuriems rodysim pasiūlymus iš DB (datalist)
SUGGESTION_FIELDS = [
    "klientas",
    "projektas",
    "metalas",
    "kabinimo_budas",
    "kabinimas_reme",
    "paruosimas",
    "padengimas",
    "padengimo_standartas",
    "spalva",
    "maskavimas",
    "testai_kokybe",
    "pakavimas",
    "instrukcija",
]


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
            "maskavimas",
            "atlikimo_terminas",
            "testai_kokybe",
            "pakavimas",
            "instrukcija",
            "pakavimo_dienos_norma",
            "pak_po_ktl",
            "pak_po_milt",
            "kaina_eur",
            "pastabos",
        ]
        widgets = {
            "atlikimo_terminas": forms.DateInput(attrs={"type": "date"}),
            "pastabos": forms.Textarea(
                attrs={
                    "rows": 3,
                    "placeholder": "Papildomos pastabos..."
                }
            ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # --- Label'ai iš COLUMNS (kad sutaptų su sąrašo stulpeliais) ---
        label_map = {
            col["key"]: col["label"]
            for col in COLUMNS
            if col.get("type") != "virtual"
        }
        for name, field in self.fields.items():
            if name in label_map:
                field.label = label_map[name]

        # --- bendras CSS klasės priskyrimas + placeholderiai kai kuriems laukams ---
        for name, field in self.fields.items():
            css = field.widget.attrs.get("class", "")
            field.widget.attrs["class"] = (css + " poz-field").strip()

            if isinstance(field.widget, forms.TextInput):
                if name == "poz_kodas":
                    field.widget.attrs.setdefault(
                        "placeholder", "Brėžinio / detalės kodas"
                    )
                elif name == "poz_pavad":
                    field.widget.attrs.setdefault(
                        "placeholder", "Detalės pavadinimas"
                    )
                elif name == "klientas":
                    field.widget.attrs.setdefault(
                        "placeholder", "Klientas"
                    )
                elif name == "projektas":
                    field.widget.attrs.setdefault(
                        "placeholder", "Projektas"
                    )

        # --- datalist hook'ai tekstiniams laukams (sufleravimui iš DB) ---
        for name in SUGGESTION_FIELDS:
            if name in self.fields:
                self.fields[name].widget.attrs.setdefault("list", f"dl-{name}")

        # --- Skaitiniai laukai – be rodyklių, bet su skaitmenų klaviatūra ---
        numeric_fields = [
            "plotas",
            "svoris",
            "detaliu_kiekis_reme",
            "faktinis_kiekis_reme",
            "pakavimo_dienos_norma",
            "pak_po_ktl",
            "pak_po_milt",
            "kaina_eur",
        ]
        for name in numeric_fields:
            if name in self.fields:
                w = self.fields[name].widget
                # vietoj type="number" -> type="text", kad nebūtų rodyklių
                w.input_type = "text"
                w.attrs.setdefault("inputmode", "decimal")
                w.attrs.setdefault("placeholder", "0")

    def save(self, commit=True):
        """
        Kuriant / redaguojant poziciją:
        - išsaugom Pozicija;
        - jei įvesta kaina_eur, sinchronizuojam su KainosEilute:
          * ieškom bazinės eilutės: vnt., nefiksuota, be kiekio ribų, busena=aktuali
          * jei yra – atnaujinam kainą
          * jei nėra – sukuriam naują eilutę
        """
        pozicija = super().save(commit=False)
        kaina = self.cleaned_data.get("kaina_eur")

        if commit:
            pozicija.save()

            if kaina is not None:
                base_qs = pozicija.kainu_eilutes.filter(
                    matas="vnt.",
                    yra_fiksuota=False,
                    kiekis_nuo__isnull=True,
                    kiekis_iki__isnull=True,
                    busena="aktuali",
                ).order_by("created")

                base = base_qs.first()

                if base:
                    base.kaina = kaina
                    base.save()
                else:
                    KainosEilute.objects.create(
                        pozicija=pozicija,
                        kaina=kaina,
                        matas="vnt.",
                        yra_fiksuota=False,
                        kiekis_nuo=None,
                        kiekis_iki=None,
                        busena="aktuali",
                        prioritetas=100,
                    )

        return pozicija


# =============================================================================
#  LEGACY: SENAS MODELIS PozicijosKaina (paliktas tik suderinamumui)
# =============================================================================

class PozicijosKainaForm(forms.ModelForm):
    class Meta:
        model = PozicijosKaina
        fields = [
            "suma",
            "kainos_matas",
            "busena",
            "yra_fiksuota",
            "kiekis_nuo",
            "kiekis_iki",
            "fiksuotas_kiekis",
        ]


PozicijosKainaFormSet = inlineformset_factory(
    Pozicija,
    PozicijosKaina,
    form=PozicijosKainaForm,
    extra=1,
    can_delete=True,
)


# =============================================================================
#  BRĖŽINIŲ FORMA
# =============================================================================

class PozicijosBrezinysForm(forms.ModelForm):
    class Meta:
        model = PozicijosBrezinys
        fields = ["pavadinimas", "failas"]
