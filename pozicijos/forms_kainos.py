# pozicijos/forms_kainos.py
from django import forms
from django.core.exceptions import ValidationError
from decimal import Decimal

from .models import KainosEilute


class KainaForm(forms.ModelForm):
    class Meta:
        model = KainosEilute
        fields = [
            "kaina", "matas",
            "yra_fiksuota", "fiksuotas_kiekis", "kiekis_nuo", "kiekis_iki",
            "galioja_nuo", "galioja_iki",
            "busena", "prioritetas", "pastaba",
        ]
        widgets = {
            "galioja_nuo": forms.DateInput(attrs={"type": "date"}),
            "galioja_iki": forms.DateInput(attrs={"type": "date"}),
        }

    def clean(self):
        data = super().clean()
        yra_fiksuota = data.get("yra_fiksuota")
        fx = data.get("fiksuotas_kiekis")
        nuo = data.get("kiekis_nuo")
        iki = data.get("kiekis_iki")

        if yra_fiksuota:
            if fx is None:
                raise ValidationError("Fiksuotai kainai reikia nurodyti „fiksuotas_kiekis“.")
            if nuo is not None or iki is not None:
                raise ValidationError("Fiksuotai kainai „kiekis_nuo/iki“ turi būti tušti.")
        else:
            if nuo is None and iki is None:
                raise ValidationError("Intervalinei kainai užpildykite bent „kiekis_nuo“ arba „kiekis_iki“. ")
            if nuo is not None and iki is not None and iki < nuo:
                raise ValidationError("„kiekis_iki“ negali būti mažesnis už „kiekis_nuo“.")

        kaina = data.get("kaina")
        try:
            if kaina is None or Decimal(kaina) < 0:
                raise ValidationError("Kaina turi būti teigiama.")
        except Exception:
            raise ValidationError("Neteisinga kainos reikšmė.")
        return data
