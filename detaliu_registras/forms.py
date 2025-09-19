from django import forms
from django.core.exceptions import ValidationError
from django.apps import apps
from .models import Uzklausa, Klientas, Projektas, Detale


# === Sąrašo filtrai (su brėžiniu, metalu, padengimu) ===
class UzklausaFilterForm(forms.Form):
    q = forms.CharField(label="Paieška", required=False)
    klientas = forms.ModelChoiceField(
        queryset=Klientas.objects.all().order_by("vardas"),
        required=False, empty_label="— visi —",
    )
    projektas = forms.ModelChoiceField(
        queryset=Projektas.objects.all().order_by("pavadinimas"),
        required=False, empty_label="— visi —",
    )
    detale = forms.ModelChoiceField(
        queryset=Detale.objects.all().order_by("pavadinimas"),
        required=False, empty_label="— visos —",
    )
    brezinio_nr = forms.CharField(label="Brėžinio nr.", required=False)
    metalas = forms.CharField(label="Metalas", required=False)
    padengimas = forms.CharField(label="Padengimas", required=False)


# === CSV importui (paprastas stub) ===
class ImportUzklausosCSVForm(forms.Form):
    file = forms.FileField(label="Pasirinkite CSV failą")


# === Nauja/Redaguojama užklausa: pasirink ARBA sukurk čia pat ===
class UzklausaCreateOrSelectForm(forms.ModelForm):
    # Klientas
    klientas = forms.ModelChoiceField(
        label="Klientas",
        queryset=Klientas.objects.all().order_by("vardas"),
        required=False, empty_label="— pasirinkite —",
    )
    naujas_klientas = forms.CharField(label="Naujas klientas", required=False)

    # Projektas
    projektas = forms.ModelChoiceField(
        label="Projektas",
        queryset=Projektas.objects.all().order_by("pavadinimas"),
        required=False, empty_label="— pasirinkite —",
    )
    naujas_projektas = forms.CharField(label="Naujas projektas", required=False)

    # Detalė
    detale = forms.ModelChoiceField(
        label="Detalė",
        queryset=Detale.objects.all().order_by("pavadinimas"),
        required=False, empty_label="— pasirinkite —",
    )
    detales_pavadinimas = forms.CharField(label="Nauja detalė – pavadinimas", required=False)
    brezinio_nr = forms.CharField(label="Brėžinio nr.", required=False)

    # Specifikacija (nebūtina)
    metalas = forms.CharField(label="Metalas", required=False)
    plotas_m2 = forms.DecimalField(label="Plotas m²", required=False, decimal_places=4, max_digits=12)
    svoris_kg = forms.DecimalField(label="Svoris kg", required=False, decimal_places=4, max_digits=12)

    # Dangos (nebūtina)
    ktl_ec_name = forms.CharField(label="KTL / e-coating", required=False)
    miltelinis_name = forms.CharField(label="Miltelinis padengimas", required=False)

    class Meta:
        model = Uzklausa
        fields = []  # modelinius laukus suformuosim save() metu

    def clean(self):
        cleaned = super().clean()
        if not cleaned.get("klientas") and not cleaned.get("naujas_klientas"):
            raise ValidationError("Pasirinkite klientą arba įveskite naują.")
        if not cleaned.get("projektas") and not cleaned.get("naujas_projektas"):
            raise ValidationError("Pasirinkite projektą arba įveskite naują.")
        turi_detale = cleaned.get("detale")
        turi_naujos_detales_duomenis = cleaned.get("detales_pavadinimas") or cleaned.get("brezinio_nr")
        if not turi_detale and not turi_naujos_detales_duomenis:
            raise ValidationError("Pasirinkite detalę arba įveskite naujos detalės duomenis.")
        return cleaned

    def save(self, commit=True):
        c = self.cleaned_data

        # Klientas
        klientas = c.get("klientas")
        if not klientas:
            klientas = Klientas.objects.create(vardas=c["naujas_klientas"].strip())

        # Projektas (susietas su klientu)
        projektas = c.get("projektas")
        if not projektas:
            projektas = Projektas.objects.create(
                pavadinimas=c["naujas_projektas"].strip(),
                klientas=klientas,
            )

        # Detalė
        detale = c.get("detale")
        if not detale:
            detale = Detale.objects.create(
                pavadinimas=c.get("detales_pavadinimas") or "Be pavadinimo",
                brezinio_nr=c.get("brezinio_nr") or "",
            )

        # Specifikacija (jei modelis egzistuoja ir kažką suvedė)
        if any([c.get("metalas"), c.get("plotas_m2") is not None, c.get("svoris_kg") is not None]):
            DetaleSpecifikacija = apps.get_model("detaliu_registras", "DetaleSpecifikacija")
            if DetaleSpecifikacija:
                spec, _ = DetaleSpecifikacija.objects.get_or_create(detale=detale)
                if c.get("metalas"):
                    spec.metalas = c["metalas"].strip()
                if c.get("plotas_m2") is not None:
                    spec.plotas_m2 = c["plotas_m2"]
                if c.get("svoris_kg") is not None:
                    spec.svoris_kg = c["svoris_kg"]
                spec.save()

        # Dangos (jei modelis egzistuoja ir kažką suvedė)
        if c.get("ktl_ec_name") or c.get("miltelinis_name"):
            PavirsiuDangos = apps.get_model("detaliu_registras", "PavirsiuDangos")
            if PavirsiuDangos:
                pd, _ = PavirsiuDangos.objects.get_or_create(detale=detale)
                if c.get("ktl_ec_name"):
                    pd.ktl_ec_name = c["ktl_ec_name"].strip()
                if c.get("miltelinis_name"):
                    pd.miltelinis_name = c["miltelinis_name"].strip()
                pd.save()

        uzk = Uzklausa(klientas=klientas, projektas=projektas, detale=detale)
        if commit:
            uzk.save()
        return uzk
