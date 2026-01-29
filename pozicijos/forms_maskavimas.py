# pozicijos/forms_maskavimas.py
from __future__ import annotations

from django import forms
from django.forms import modelformset_factory

from .models import MaskavimoEilute


class MaskavimoEiluteForm(forms.ModelForm):
    class Meta:
        model = MaskavimoEilute
        fields = ["maskuote", "vietu_kiekis", "aprasymas"]
        widgets = {
            "maskuote": forms.TextInput(attrs={"placeholder": "Tipas"}),
            "vietu_kiekis": forms.NumberInput(attrs={"min": 0, "step": 1, "inputmode": "numeric", "placeholder": "Kiekis"}),
            "aprasymas": forms.Textarea(attrs={"rows": 2, "placeholder": "Aprašymas", "data-autoresize": "1"}),
        }


MaskavimoFormSet = modelformset_factory(
    MaskavimoEilute,
    form=MaskavimoEiluteForm,
    extra=0,
    can_delete=True,
)
