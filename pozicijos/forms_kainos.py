# pozicijos/forms_kainos.py
from decimal import Decimal

from django import forms
from django.core.exceptions import ValidationError
from django.forms import inlineformset_factory

from .models import Pozicija, KainosEilute


class KainaForm(forms.ModelForm):
    """
    Vienos KainosEilute eilutės forma.
    Naudojama inline formsete ant Pozicija (variantas A – vienas langas).
    """

    class Meta:
        model = KainosEilute
        fields = [
            "kaina",
            "matas",
            "yra_fiksuota",
            "fiksuotas_kiekis",
            "kiekis_nuo",
            "kiekis_iki",
            "galioja_nuo",
            "galioja_iki",
            "busena",
            "prioritetas",
            "pastaba",
        ]
        widgets = {
            "kaina": forms.NumberInput(attrs={
                "step": "0.01",
                "min": "0",
                "style": "width:100px",
            }),
            "matas": forms.Select(attrs={"style": "width:80px"}),
            "yra_fiksuota": forms.CheckboxInput(),
            "fiksuotas_kiekis": forms.NumberInput(attrs={"style": "width:80px"}),
            "kiekis_nuo": forms.NumberInput(attrs={"style": "width:80px"}),
            "kiekis_iki": forms.NumberInput(attrs={"style": "width:80px"}),
            "galioja_nuo": forms.DateInput(attrs={
                "type": "date",
                "style": "width:130px",
            }),
            "galioja_iki": forms.DateInput(attrs={
                "type": "date",
                "style": "width:130px",
            }),
            "busena": forms.Select(attrs={"style": "width:110px"}),
            "prioritetas": forms.NumberInput(attrs={"style": "width:70px"}),
            "pastaba": forms.TextInput(attrs={"style": "width:100%;"}),
        }

    def clean(self):
        """
        Sujungta tavo sena logika:
        - kaina privaloma ir turi būti teigiama;
        - tvarkingas fiksuota / intervalinė atskyrimas;
        - 'empty' formos formsete praleidžiamos.
        """
        cleaned = super().clean()

        # jei forma formsete visiškai tuščia ir leidžiama praleisti – tikrai netikrinam
        if self.empty_permitted and not self.has_changed():
            return cleaned

        yra_fiksuota = cleaned.get("yra_fiksuota")
        fiksuotas_kiekis = cleaned.get("fiksuotas_kiekis")
        kiekis_nuo = cleaned.get("kiekis_nuo")
        kiekis_iki = cleaned.get("kiekis_iki")
        kaina = cleaned.get("kaina")
        matas = cleaned.get("matas")

        # --- Kaina: privaloma ir teigiama ---
        try:
            if kaina is None or Decimal(kaina) < 0:
                raise ValidationError("Kaina turi būti teigiama.")
        except Exception:
            raise ValidationError("Neteisinga kainos reikšmė.")

        # --- Matas: privalomas ---
        if not matas:
            raise ValidationError("Pasirinkite matą.")

        # --- Fiksuota / intervalinė logika (tavo sena schema) ---
        if yra_fiksuota:
            # Fiksuota: privalomas fiksuotas_kiekis, kiekis_nuo/iki turi būti tušti
            if fiksuotas_kiekis is None:
                raise ValidationError("Fiksuotai kainai reikia nurodyti „Fiksuotas kiekis“.")
            if kiekis_nuo is not None or kiekis_iki is not None:
                raise ValidationError("Fiksuotai kainai „Kiekis nuo/iki“ turi būti tušti.")
        else:
            # Intervalinė: bent vienas iš nuo/iki turi būti užpildytas
            if kiekis_nuo is None and kiekis_iki is None:
                raise ValidationError(
                    "Intervalinei kainai užpildykite bent „Kiekis nuo“ arba „Kiekis iki“."
                )
            if (
                kiekis_nuo is not None
                and kiekis_iki is not None
                and kiekis_iki < kiekis_nuo
            ):
                raise ValidationError("„Kiekis iki“ negali būti mažesnis už „Kiekis nuo“.")

        return cleaned


KainaFormSet = inlineformset_factory(
    Pozicija,
    KainosEilute,
    form=KainaForm,
    extra=1,        # visada bent viena tuščia eilutė
    can_delete=True,
)
