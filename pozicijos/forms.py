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
    "pakavimas",
    "instrukcija",
]

# Privalomi laukai (loginė „būtina“ bazė)
REQUIRED_FIELDS = [
    "klientas",
    "poz_kodas",
    "poz_pavad",
    "metalas",
    "padengimas",
]

# Individualūs LT tekstai privalomiems laukams
REQUIRED_MESSAGES = {
    "klientas": "Nurodykite klientą.",
    "poz_kodas": "Nurodykite brėžinio / detalės kodą.",
    "poz_pavad": "Nurodykite detalės pavadinimą.",
    "metalas": "Nurodykite metalo tipą.",
    "padengimas": "Nurodykite padengimo tipą.",
}


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
            # Paslaugos blokas
            "paslauga_ktl",
            "paslauga_miltai",
            "paslauga_paruosimas",
            "paruosimas",
            "padengimas",
            "padengimo_standartas",
            "spalva",
            "miltu_kodas",
            "miltu_spalva",
            "miltu_tiekejas",
            "miltu_blizgumas",
            "miltu_kaina",
            # Maskavimas
            "maskavimo_tipas",
            "maskavimas",
            # Terminai / testai
            "atlikimo_terminas",
            "testai_kokybe",
            # Pakavimas
            "pakavimo_tipas",
            "pakavimas",
            "instrukcija",
            # Kaina + pastabos
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

        # --- Privalomi laukai + LT 'required' klaidos ---
        for name in REQUIRED_FIELDS:
            if name in self.fields:
                field = self.fields[name]
                field.required = True
                msg = REQUIRED_MESSAGES.get(name, "Šis laukas privalomas.")
                field.error_messages["required"] = msg

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
            "kaina_eur",
            "miltu_kaina",
        ]
        for name in numeric_fields:
            if name in self.fields:
                field = self.fields[name]
                w = field.widget
                # vietoj type="number" -> type="text", kad nebūtų rodyklių
                w.input_type = "text"
                w.attrs.setdefault("inputmode", "decimal")
                w.attrs.setdefault("placeholder", "0")
                field.error_messages.setdefault(
                    "invalid",
                    "Įveskite skaičių (pvz. 12.5).",
                )

    def clean(self):
        cleaned = super().clean()

        # --- Paslaugos: KTL / Miltai / Paruošimas ---
        ktl = cleaned.get("paslauga_ktl")
        miltai = cleaned.get("paslauga_miltai")
        par_flag = cleaned.get("paslauga_paruosimas")

        paruosimas = (cleaned.get("paruosimas") or "").strip()
        padengimas = (cleaned.get("padengimas") or "").strip()

        # KTL + Paruošimas kartu negalima
        if ktl and par_flag:
            self.add_error("paslauga_paruosimas", "Negalima žymėti „Paruošimas“, kai pasirinktas KTL.")

        # Jei yra KTL arba Paruošimas – privalomas paruošimas
        if (ktl or par_flag) and not paruosimas:
            self.add_error("paruosimas", "KTL / Paruošimo atveju paruošimas yra privalomas.")

        # Jei KTL – privalomas padengimas
        if ktl and not padengimas:
            self.add_error("padengimas", "KTL atveju privalomas padengimas.")

        # Miltai – privalomi kodas ir kaina
        miltu_kodas = (cleaned.get("miltu_kodas") or "").strip()
        miltu_kaina = cleaned.get("miltu_kaina")

        if miltai:
            if not miltu_kodas:
                self.add_error("miltu_kodas", "Miltų paslaugai būtinas kodas.")
            if miltu_kaina in (None, ""):
                self.add_error("miltu_kaina", "Miltų paslaugai būtina kaina.")

        cleaned["paruosimas"] = paruosimas or None
        cleaned["padengimas"] = padengimas or None
        cleaned["miltu_kodas"] = miltu_kodas or None

        # --- Pakavimas ---
        pakavimo_tipas = cleaned.get("pakavimo_tipas")
        pakavimas = (cleaned.get("pakavimas") or "").strip()

        PAK_TEMPLATES = {
            "palaidas": "Palaidas pakavimas pagal standartinę procedūrą.",
            "standartinis": "Standartinis pakavimas: kartoninė dėžė, apsauga nuo pažeidimų.",
            "geras": "Pagerintas pakavimas su papildoma apsauga ir atskyrimu.",
            "individualus": "Individualus pakavimas pagal kliento poreikius.",
        }

        if pakavimo_tipas in PAK_TEMPLATES and not pakavimas:
            pakavimas = PAK_TEMPLATES[pakavimo_tipas]

        if pakavimo_tipas == "individualus" and not pakavimas:
            self.add_error("pakavimas", "Individualiam pakavimui aprašymas yra privalomas.")

        cleaned["pakavimas"] = pakavimas or None

        # --- Maskavimas ---
        maskavimo_tipas = cleaned.get("maskavimo_tipas")
        maskavimas = (cleaned.get("maskavimas") or "").strip()

        MAS_TEMPLATES = {
            "iprastas": "Įprastas maskavimas pagal standartinę schemą.",
            "specialus": "Specialus maskavimas pagal atskirą susitarimą ir brėžinio nurodymus.",
        }

        if maskavimo_tipas in MAS_TEMPLATES and not maskavimas:
            maskavimas = MAS_TEMPLATES[maskavimo_tipas]

        cleaned["maskavimas"] = maskavimas or None

        return cleaned

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
