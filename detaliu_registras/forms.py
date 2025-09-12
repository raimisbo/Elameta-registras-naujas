from django import forms
from .models import Klientas, Projektas, Detale, Kaina, Uzklausa, Danga

# CSV importas: suderinta su views (laukas 'file')
class ImportCSVForm(forms.Form):
    file = forms.FileField(label="CSV failas")


class UzklausaFilterForm(forms.Form):
    q = forms.CharField(
        required=False,
        label='Ieškoti',
        widget=forms.TextInput(attrs={'placeholder': 'Ieškoti...'})
    )


# --- Model forms ---

class KlientasForm(forms.ModelForm):
    class Meta:
        model = Klientas
        # el_pastas – kad atitiktų modelį/servisą (ne 'email')
        fields = ['vardas', 'adresas', 'telefonas', 'el_pastas']
        widgets = {
            'el_pastas': forms.EmailInput(),
        }


class ProjektasForm(forms.ModelForm):
    class Meta:
        model = Projektas
        fields = ['klientas', 'pavadinimas', 'uzklausos_data', 'pasiulymo_data']
        widgets = {
            'uzklausos_data': forms.DateInput(attrs={'type': 'date'}),
            'pasiulymo_data': forms.DateInput(attrs={'type': 'date'}),
        }


class DetaleForm(forms.ModelForm):
    class Meta:
        model = Detale
        fields = [
            'pavadinimas', 'brezinio_nr', 'plotas', 'svoris',
            'kiekis_metinis', 'kiekis_menesis', 'kiekis_partijai',
            'ppap_dokumentai', 'danga', 'standartas', 'kabinimo_tipas',
            'kabinimas_xyz', 'kiekis_reme', 'faktinis_kiekis_reme',
            'pakavimas', 'nuoroda_brezinio', 'nuoroda_pasiulymo', 'pastabos'
        ]
        widgets = {
            'danga': forms.CheckboxSelectMultiple(),
            'ppap_dokumentai': forms.Textarea(attrs={'rows': 3}),
            'pastabos': forms.Textarea(attrs={'rows': 3}),
            'faktinis_kiekis_reme': forms.NumberInput(attrs={'value': 0}),
        }


class KainaForm(forms.ModelForm):
    class Meta:
        model = Kaina
        # Pašalinam 'yra_fiksuota' (jei jo nėra modelyje).
        fields = ['busena', 'suma', 'kiekis_nuo', 'kiekis_iki',
                  'fiksuotas_kiekis', 'kainos_matas']
        widgets = {
            'kiekis_nuo': forms.NumberInput(attrs={'min': 0}),
            'kiekis_iki': forms.NumberInput(attrs={'min': 0}),
            'fiksuotas_kiekis': forms.NumberInput(attrs={'value': 100, 'min': 0}),
        }

    def clean(self):
        cleaned_data = super().clean()
        kiekis_nuo = cleaned_data.get('kiekis_nuo')
        kiekis_iki = cleaned_data.get('kiekis_iki')

        # Intervalo validacija (jei abu duoti)
        if kiekis_nuo is not None and kiekis_iki is not None and kiekis_nuo >= kiekis_iki:
            raise forms.ValidationError("Kiekis 'nuo' turi būti mažesnis nei 'iki'")
        return cleaned_data


# --- Kompozitinė forma pilnam kūrimui (Klientas -> Projektas -> Detale -> Uzklausa) ---

class UzklausaCreationForm(forms.Form):
    """
    Composite form that handles creating:
    Klientas -> Projektas -> Detale -> Uzklausa
    Suderinta su UzklausaService.create_full_request(form.cleaned_data)
    """

    # Client selection or creation
    existing_klientas = forms.ModelChoiceField(
        queryset=Klientas.objects.all(),
        required=False,
        label="Pasirinkti esamą klientą"
    )
    new_klientas_vardas = forms.CharField(
        max_length=100,
        required=False,
        label="Arba įvesti naują klientą"
    )

    # Project data
    projekto_pavadinimas = forms.CharField(max_length=255, label="Projekto pavadinimas")
    uzklausos_data = forms.DateField(
        widget=forms.DateInput(attrs={'type': 'date'}),
        label="Užklausos data"
    )
    pasiulymo_data = forms.DateField(
        widget=forms.DateInput(attrs={'type': 'date'}),
        label="Pasiūlymo data"
    )

    # (nebūtina) Detalės baziniai laukai – jei nori, gali pridėti ir mapinti į services.py -> detale_fields
    # detale_pavadinimas = forms.CharField(max_length=255, required=False, label="Detalės pavadinimas")
    # detale_brezinio_nr = forms.CharField(max_length=255, required=False, label="Brėžinio nr.")

    def clean(self):
        cleaned_data = super().clean()
        existing_klientas = cleaned_data.get('existing_klientas')
        new_klientas_vardas = cleaned_data.get('new_klientas_vardas')

        if not existing_klientas and not new_klientas_vardas:
            raise forms.ValidationError("Pasirinkite klientą arba įveskite naują")

        if existing_klientas and new_klientas_vardas:
            raise forms.ValidationError("Pasirinkite tik vieną variantą")

        return cleaned_data
