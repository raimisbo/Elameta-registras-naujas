# pozicijos/forms_maskavimas.py
from __future__ import annotations

from django import forms
from django.forms import modelformset_factory

from .models import MaskavimoEilute


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
