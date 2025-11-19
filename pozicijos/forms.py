# pozicijos/forms.py
from django import forms
from django.forms import inlineformset_factory

from .models import Pozicija, PozicijosKaina, PozicijosBrezinys, KainosEilute


# =============================================================================
#  PAGRINDINĖ POZICIJOS FORMA  (naudojama dabar)
# =============================================================================

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
    }

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
#  ŠIOS FORMOS DABAR NĖRA NAUDOJAMOS NAUJOJE ARCHITEKTŪROJE.
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
#  BRĖŽINIŲ FORMA  (naudojama dabar)
# =============================================================================

class PozicijosBrezinysForm(forms.ModelForm):
    class Meta:
        model = PozicijosBrezinys
        fields = ["pavadinimas", "failas"]
