from django import forms
from .models import Klientas, Projektas, Detale, Kaina, Uzklausa, Danga

class ImportCSVForm(forms.Form):
    csv_file = forms.FileField()

class ImportCSVForm(forms.Form):
    csv_file = forms.FileField()
    
'''class UzklausaSearchForm(forms.Form):
    search_term = forms.CharField(label='Paieškos Terminas', max_length=100, required=False)'''

class UzklausaFilterForm(forms.Form):
    q = forms.CharField(required=False, label='Ieškoti', widget=forms.TextInput(attrs={'placeholder': 'Ieškoti...'}))

class IvestiUzklausaForm(forms.ModelForm):
    klientas = forms.ModelChoiceField(queryset=Klientas.objects.all(), label="Klientas")
    projekto_pavadinimas = forms.CharField(max_length=255, label="Projekto pavadinimas")
    uzklausos_data = forms.DateField(widget=forms.DateInput(attrs={'type': 'date', 'format': '%Y-%m-%d'}), label="Užklausos data")
    pasiulymo_data = forms.DateField(widget=forms.DateInput(attrs={'type': 'date', 'format': '%Y-%m-%d'}), label="Pasiūlymo data")
    detales_pavadinimas = forms.CharField(max_length=255, label="Detalės pavadinimas")
    brezinio_nr = forms.CharField(max_length=255, label="Brėžinio Nr")
    plotas = forms.FloatField(label="Plotas")
    svoris = forms.FloatField(label="Svoris")
    kiekis_metinis = forms.IntegerField(label="Metinis kiekis")
    kiekis_menesis = forms.IntegerField(required=False, label="Mėnesio kiekis")
    kiekis_partijai = forms.IntegerField(required=False, label="Partijos kiekis")
    ppap_dokumentai = forms.CharField(widget=forms.Textarea, required=False, label="PPAP dokumentai")
    danga = forms.ModelMultipleChoiceField(queryset=Danga.objects.all(), widget=forms.CheckboxSelectMultiple, required=False, label="Danga")
    standartas = forms.CharField(max_length=255, required=False, label="Standartas")
    kabinimo_tipas = forms.CharField(max_length=255, required=False, label="Kabinimo tipas")
    kabinimas_xyz = forms.CharField(max_length=255, required=False, label="Kabinimas XYZ")
    kiekis_reme = forms.IntegerField(label="Kiekis rėme")
    faktinis_kiekis_reme = forms.IntegerField(required=False, initial=0, label="Faktinis kiekis rėme")
    pakavimas = forms.CharField(max_length=255, required=False, label="Pakavimas")
    nuoroda_brezinio = forms.CharField(max_length=255, required=False, label="Nuoroda į brėžinį")
    nuoroda_pasiulymo = forms.CharField(max_length=255, label="Nuoroda į pasiūlymą")
    pastabos = forms.CharField(widget=forms.Textarea, required=False, label="Pastabos")

    class Meta:
        model = Uzklausa
        fields = ['klientas', 'projekto_pavadinimas', 'uzklausos_data', 'pasiulymo_data', 'detales_pavadinimas',
                  'brezinio_nr', 'plotas', 'svoris', 'kiekis_metinis', 'kiekis_menesis', 'kiekis_partijai',
                  'ppap_dokumentai', 'danga', 'standartas', 'kabinimo_tipas', 'kabinimas_xyz', 'kiekis_reme',
                  'faktinis_kiekis_reme', 'pakavimas', 'nuoroda_brezinio', 'nuoroda_pasiulymo', 'pastabos']

class KainaForm(forms.ModelForm):
    busena = forms.ChoiceField(choices=[('aktuali', 'aktuali'), ('sena', 'sena')], initial='aktuali')
    kainos_matas = forms.ChoiceField(choices=Kaina.MATAS_CHOICES, initial='vnt.')
    
    class Meta:
        model = Kaina
        fields = ['busena', 'suma', 'kiekis_nuo', 'kiekis_iki', 'fiksuotas_kiekis', 'kainos_matas']
        widgets = {
            'kiekis_nuo': forms.NumberInput(attrs={'min': 0}),
            'kiekis_iki': forms.NumberInput(attrs={'min': 0}),
            'fiksuotas_kiekis': forms.NumberInput(attrs={'value': 100, 'min': 0}),
        }