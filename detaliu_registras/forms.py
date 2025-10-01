# -*- coding: utf-8 -*-
from decimal import Decimal, InvalidOperation

from django import forms
from django.utils import timezone

from .models import Uzklausa, Kaina, Klientas, Projektas, Detale


# === Filtras sąrašui (kaina_nuo/kaina_iki priima ir kablelį) ===
class UzklausaFilterForm(forms.Form):
    q = forms.CharField(required=False, label="Paieška")
    klientas = forms.ModelChoiceField(queryset=Klientas.objects.all(), required=False, label="Klientas")
    projektas = forms.ModelChoiceField(queryset=Projektas.objects.all(), required=False, label="Projektas")
    detale = forms.ModelChoiceField(queryset=Detale.objects.all(), required=False, label="Detalė")
    brezinio_nr = forms.CharField(required=False, label="Brėžinio Nr.")
    metalas = forms.CharField(required=False, label="Metalas")
    padengimas = forms.CharField(required=False, label="Padengimas")

    # Pakeista į CharField, kad galėtume patys normalizuoti kablelį
    kaina_nuo = forms.CharField(required=False, label="Kaina nuo (€)")
    kaina_iki = forms.CharField(required=False, label="Kaina iki (€)")

    def clean(self):
        cleaned = super().clean()

        def parse_decimal(name):
            raw = cleaned.get(name)
            if raw in (None, ""):
                cleaned[name] = None
                return
            s = str(raw).strip().replace(" ", "").replace(",", ".")
            try:
                cleaned[name] = Decimal(s)
            except (InvalidOperation, ValueError):
                self.add_error(name, "Įveskite teisingą skaičių (pvz., 2,70 arba 2.70).")

        parse_decimal("kaina_nuo")
        parse_decimal("kaina_iki")
        return cleaned


# === Užklausos sukūrimas / pasirinkimas ===
class UzklausaCreateOrSelectForm(forms.ModelForm):
    class Meta:
        model = Uzklausa
        fields = "__all__"  # pritaikyk pagal poreikį


# === Užklausos redagavimas ===
class UzklausaEditForm(forms.ModelForm):
    class Meta:
        model = Uzklausa
        fields = "__all__"  # pritaikyk pagal poreikį


# === CSV importas ===
class ImportUzklausosCSVForm(forms.Form):
    file = forms.FileField(required=True, label="CSV failas")


# === Kainos formos ===
class KainaForm(forms.ModelForm):
    """
    Skirta inline formset ir paprastam redagavimui.
    - Valiuta paslepiama ir visada fiksuojama į 'EUR'.
    - Jei nėra 'galioja_nuo' – nustatomas dabar (jei toks laukas egzistuoja).
    """
    class Meta:
        model = Kaina
        fields = "__all__"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Valiutos lauko nerodome; pradinė reikšmė EUR naujam įrašui
        if "valiuta" in self.fields:
            self.fields["valiuta"].widget = forms.HiddenInput()
            if not getattr(self.instance, "pk", None):
                self.fields["valiuta"].initial = "EUR"

    def clean(self):
        data = super().clean()
        if "valiuta" in data:
            data["valiuta"] = "EUR"
        return data

    def save(self, commit=True):
        obj = super().save(commit=False)

        # Užfiksuoti EUR modelio lygiu
        if hasattr(obj, "valiuta"):
            obj.valiuta = "EUR"

        # Jei nėra datos nuo – nustatome dabar (jei toks laukas egzistuoja)
        if hasattr(obj, "galioja_nuo") and not getattr(obj, "galioja_nuo", None):
            try:
                obj.galioja_nuo = timezone.now()
            except Exception:
                pass

        if commit:
            obj.save()
        return obj


class KainaRedagavimoForm(forms.Form):
    """
    Forma „pridėti/keisti kainą“ (vieno įrašo atvejis).
    Valiuta nerodoma, visada EUR.
    """
    suma = forms.CharField(required=True, label="Suma (€)")
    valiuta = forms.CharField(required=False, initial="EUR", widget=forms.HiddenInput())
    keitimo_priezastis = forms.CharField(required=False, label="Priežastis")

    def clean_suma(self):
        raw = self.cleaned_data.get("suma")
        s = str(raw).strip().replace(" ", "").replace(",", ".")
        try:
            return Decimal(s)
        except (InvalidOperation, ValueError):
            raise forms.ValidationError("Įveskite teisingą sumą (pvz., 2,70 arba 2.70).")

    def clean_valiuta(self):
        return "EUR"
