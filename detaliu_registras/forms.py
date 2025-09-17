# detaliu_registras/forms.py
from __future__ import annotations

from django import forms
from django.forms import inlineformset_factory, BaseInlineFormSet
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _

from .models import (
    Klientas, Projektas, Detale, Uzklausa, Kaina,
    UzklausosProjektoDuomenys, DetalesIdentifikacija, PavirsiaiDangos,
    DetalesSpecifikacija, KiekiaiTerminai, KabinimasRemai, Pakavimas,
    Kainodara, KainosPartijai, Pastaba
)


# ======== BENDRI WIDGET NAUDAI ========
_DEFAULT_INPUT_CSS = {"class": "form-input"}
_DEFAULT_TEXTAREA_CSS = {"class": "form-textarea", "rows": 3}
_DEFAULT_NUMBER_CSS = {"class": "form-input", "step": "0.01"}
_DEFAULT_DATE_CSS = {"class": "form-input", "type": "date"}

def number_widget(step="0.01", min_val=None):
    attrs = dict(_DEFAULT_NUMBER_CSS)
    attrs["step"] = step
    if min_val is not None:
        attrs["min"] = str(min_val)
    return forms.NumberInput(attrs=attrs)


# ======== ESAMŲ PAGRINDINIŲ MODELIŲ FORMOS (saugiai) ========
class KlientasForm(forms.ModelForm):
    class Meta:
        model = Klientas
        fields = ["vardas", "el_pastas"]
        widgets = {
            "vardas": forms.TextInput(attrs=_DEFAULT_INPUT_CSS),
            "el_pastas": forms.EmailInput(attrs=_DEFAULT_INPUT_CSS),
        }


class ProjektasForm(forms.ModelForm):
    class Meta:
        model = Projektas
        fields = ["klientas", "pavadinimas", "aprasymas"]
        widgets = {
            "klientas": forms.Select(attrs=_DEFAULT_INPUT_CSS),
            "pavadinimas": forms.TextInput(attrs=_DEFAULT_INPUT_CSS),
            "aprasymas": forms.Textarea(attrs=_DEFAULT_TEXTAREA_CSS),
        }


class DetaleForm(forms.ModelForm):
    class Meta:
        model = Detale
        fields = ["projektas", "pavadinimas", "brezinio_nr", "kiekis"]
        widgets = {
            "projektas": forms.Select(attrs=_DEFAULT_INPUT_CSS),
            "pavadinimas": forms.TextInput(attrs=_DEFAULT_INPUT_CSS),
            "brezinio_nr": forms.TextInput(attrs=_DEFAULT_INPUT_CSS),
            "kiekis": number_widget(step="1", min_val=0),
        }


class UzklausaForm(forms.ModelForm):
    class Meta:
        model = Uzklausa
        fields = ["klientas", "projektas", "detale"]
        widgets = {
            "klientas": forms.Select(attrs=_DEFAULT_INPUT_CSS),
            "projektas": forms.Select(attrs=_DEFAULT_INPUT_CSS),
            "detale": forms.Select(attrs=_DEFAULT_INPUT_CSS),
        }


# ======== 1) PROJEKTO DUOMENYS ========
class UzklausosProjektoDuomenysForm(forms.ModelForm):
    class Meta:
        model = UzklausosProjektoDuomenys
        fields = [
            "uzklausos_nr", "uzklausos_data", "pasiulymo_data",
            "projekto_pradzia_metai", "projekto_pabaiga_metai",
            "kaina_vnt", "kaina_galioja_iki",
            "apmokejimo_salygos", "transportavimo_salygos",
            "atsakingas",
        ]
        widgets = {
            "uzklausos_nr": forms.TextInput(attrs=_DEFAULT_INPUT_CSS),
            "uzklausos_data": forms.DateInput(attrs=_DEFAULT_DATE_CSS),
            "pasiulymo_data": forms.DateInput(attrs=_DEFAULT_DATE_CSS),
            "projekto_pradzia_metai": number_widget(step="1", min_val=1900),
            "projekto_pabaiga_metai": number_widget(step="1", min_val=1900),
            "kaina_vnt": number_widget(step="0.0001", min_val=0),
            "kaina_galioja_iki": forms.DateInput(attrs=_DEFAULT_DATE_CSS),
            "apmokejimo_salygos": forms.TextInput(attrs=_DEFAULT_INPUT_CSS),
            "transportavimo_salygos": forms.TextInput(attrs=_DEFAULT_INPUT_CSS),
            "atsakingas": forms.Select(attrs=_DEFAULT_INPUT_CSS),
        }

    def clean(self):
        data = super().clean()
        start = data.get("projekto_pradzia_metai")
        end = data.get("projekto_pabaiga_metai")
        if start and end and end < start:
            raise ValidationError(_("Projekto pabaigos metai negali būti ankstesni nei pradžios."))
        return data


# ======== 2) DETALĖS IDENTIFIKACIJA ========
class DetalesIdentifikacijaForm(forms.ModelForm):
    class Meta:
        model = DetalesIdentifikacija
        fields = ["pavadinimas", "brezinio_numeris", "paruosimas"]
        widgets = {
            "pavadinimas": forms.TextInput(attrs=_DEFAULT_INPUT_CSS),
            "brezinio_numeris": forms.TextInput(attrs=_DEFAULT_INPUT_CSS),
            "paruosimas": forms.Textarea(attrs=_DEFAULT_TEXTAREA_CSS),
        }


# ======== 3) PAVIRŠIAI / DANGOS ========
class PavirsiaiDangosForm(forms.ModelForm):
    class Meta:
        model = PavirsiaiDangos
        fields = [
            "ktl_ec_name", "miltelinis_name",
            "storis_ktl_mkm", "storis_ktl_plus_miltai_mkm",
            "padengimo_standartas", "testai",
        ]
        widgets = {
            "ktl_ec_name": forms.TextInput(attrs=_DEFAULT_INPUT_CSS),
            "miltelinis_name": forms.TextInput(attrs=_DEFAULT_INPUT_CSS),
            "storis_ktl_mkm": number_widget(step="0.01", min_val=0),
            "storis_ktl_plus_miltai_mkm": number_widget(step="0.01", min_val=0),
            "padengimo_standartas": forms.TextInput(attrs=_DEFAULT_INPUT_CSS),
            "testai": forms.Textarea(attrs=_DEFAULT_TEXTAREA_CSS),
        }


# ======== 4) MATMENYS & MEDŽIAGA ========
class DetalesSpecifikacijaForm(forms.ModelForm):
    class Meta:
        model = DetalesSpecifikacija
        fields = [
            "aukstis_x_cm", "plotis_y_cm", "ilgis_z_cm",
            "metalo_storis_mm", "svoris_kg", "plotas_m2", "metalas",
        ]
        widgets = {
            "aukstis_x_cm": number_widget(step="0.01", min_val=0),
            "plotis_y_cm": number_widget(step="0.01", min_val=0),
            "ilgis_z_cm": number_widget(step="0.01", min_val=0),
            "metalo_storis_mm": number_widget(step="0.001", min_val=0),
            "svoris_kg": number_widget(step="0.0001", min_val=0),
            "plotas_m2": number_widget(step="0.000001", min_val=0),
            "metalas": forms.TextInput(attrs=_DEFAULT_INPUT_CSS),
        }


# ======== 5) KIEKIAI & TERMINAI ========
class KiekiaiTerminaiForm(forms.ModelForm):
    class Meta:
        model = KiekiaiTerminai
        fields = ["metinis_kiekis_vnt", "partijos_dydis_vnt", "minimalus_kiekis_vnt", "terminai_darbo_dienomis"]
        widgets = {
            "metinis_kiekis_vnt": number_widget(step="1", min_val=0),
            "partijos_dydis_vnt": number_widget(step="1", min_val=0),
            "minimalus_kiekis_vnt": number_widget(step="1", min_val=0),
            "terminai_darbo_dienomis": number_widget(step="1", min_val=0),
        }


# ======== 6) KABINIMAS / RĖMAI ========
class KabinimasRemaiForm(forms.ModelForm):
    class Meta:
        model = KabinimasRemai
        fields = [
            "kabinimo_budas", "kiekis_reme_planuotas", "kiekis_reme_faktinis",
            "kabliukai", "spyruoke",
            "kontaktines_vietos_ktl", "kontaktines_vietos_miltelinis",
            "nepilnas_remas", "sukabinimo_dienos_norma_vnt", "pakavimo_dienos_norma_vnt",
        ]
        widgets = {
            "kabinimo_budas": forms.Select(attrs=_DEFAULT_INPUT_CSS),
            "kiekis_reme_planuotas": number_widget(step="1", min_val=0),
            "kiekis_reme_faktinis": number_widget(step="1", min_val=0),
            "kabliukai": forms.TextInput(attrs=_DEFAULT_INPUT_CSS),
            "spyruoke": forms.TextInput(attrs=_DEFAULT_INPUT_CSS),
            "kontaktines_vietos_ktl": forms.Textarea(attrs=_DEFAULT_TEXTAREA_CSS),
            "kontaktines_vietos_miltelinis": forms.Textarea(attrs=_DEFAULT_TEXTAREA_CSS),
            "nepilnas_remas": forms.CheckboxInput(attrs={"class": "form-checkbox"}),
            "sukabinimo_dienos_norma_vnt": number_widget(step="1", min_val=0),
            "pakavimo_dienos_norma_vnt": number_widget(step="1", min_val=0),
        }


# ======== 7) PAKAVIMAS ========
class PakavimasForm(forms.ModelForm):
    class Meta:
        model = Pakavimas
        fields = ["tara", "pakavimo_instrukcija", "pakavimas_po_ktl", "pakavimas_po_miltelinio", "papildomos_paslaugos"]
        widgets = {
            "tara": forms.TextInput(attrs=_DEFAULT_INPUT_CSS),
            "pakavimo_instrukcija": forms.Textarea(attrs=_DEFAULT_TEXTAREA_CSS),
            "pakavimas_po_ktl": forms.Textarea(attrs=_DEFAULT_TEXTAREA_CSS),
            "pakavimas_po_miltelinio": forms.Textarea(attrs=_DEFAULT_TEXTAREA_CSS),
            "papildomos_paslaugos": forms.Textarea(attrs=_DEFAULT_TEXTAREA_CSS),
        }


# ======== 8) KAINODARA ========
class KainodaraForm(forms.ModelForm):
    class Meta:
        model = Kainodara
        fields = [
            "kabliuku_kaina_vnt", "pakavimo_medziagu_kaina_vnt", "milteliniu_dazu_kaina_kg",
            "darbo_kaina", "viso_savikaina", "fiksuota_kaina_vnt", "remo_kaina",
            "faktine_kaina", "sukabinimas_pagal_fakta", "valiuta",
        ]
        widgets = {
            "kabliuku_kaina_vnt": number_widget(step="0.0001", min_val=0),
            "pakavimo_medziagu_kaina_vnt": number_widget(step="0.0001", min_val=0),
            "milteliniu_dazu_kaina_kg": number_widget(step="0.0001", min_val=0),
            "darbo_kaina": number_widget(step="0.0001", min_val=0),
            "viso_savikaina": number_widget(step="0.0001", min_val=0),
            "fiksuota_kaina_vnt": number_widget(step="0.0001", min_val=0),
            "remo_kaina": number_widget(step="0.0001", min_val=0),
            "faktine_kaina": number_widget(step="0.0001", min_val=0),
            "sukabinimas_pagal_fakta": number_widget(step="1", min_val=0),
            "valiuta": forms.TextInput(attrs=_DEFAULT_INPUT_CSS),
        }


class KainosPartijaiForm(forms.ModelForm):
    class Meta:
        model = KainosPartijai
        fields = ["partijos_kiekis_vnt", "kaina_bendra"]
        widgets = {
            "partijos_kiekis_vnt": number_widget(step="1", min_val=1),
            "kaina_bendra": number_widget(step="0.0001", min_val=0),
        }

    def clean_partijos_kiekis_vnt(self):
        v = self.cleaned_data.get("partijos_kiekis_vnt")
        if v is not None and v <= 0:
            raise ValidationError(_("Partijos kiekis turi būti > 0."))
        return v


class BaseKainosPartijaiFormSet(BaseInlineFormSet):
    """
    Užtikrina, kad tame pačiame formsete nesikartotų 'partijos_kiekis_vnt'.
    """
    def clean(self):
        super().clean()
        seen = set()
        for form in self.forms:
            if getattr(form, "cleaned_data", None) and not form.cleaned_data.get("DELETE", False):
                qty = form.cleaned_data.get("partijos_kiekis_vnt")
                if qty:
                    if qty in seen:
                        raise ValidationError(_("Keli įrašai su tuo pačiu 'Partijos kiekis vnt.'"))
                    seen.add(qty)


def build_kainos_partijai_formset(extra: int = 3, can_delete: bool = True):
    return inlineformset_factory(
        parent_model=Kainodara,
        model=KainosPartijai,
        form=KainosPartijaiForm,
        formset=BaseKainosPartijaiFormSet,
        fields=["partijos_kiekis_vnt", "kaina_bendra"],
        extra=extra,
        can_delete=can_delete,
    )


# ======== 9) PASTABOS ========
class PastabaForm(forms.ModelForm):
    class Meta:
        model = Pastaba
        fields = ["kategorija", "tekstas"]
        widgets = {
            "kategorija": forms.Select(attrs=_DEFAULT_INPUT_CSS),
            "tekstas": forms.Textarea(attrs={"class": "form-textarea", "rows": 4}),
        }


# ======== PAGALBINIAI KOMPOZICINIAI „PAKETAI“ (nebūtina, bet patogu) ========
class UzklausaBlokuSet:
    """
    Pagalbinė klasė, kad vienoje vietoje laikytum visų sub-formų rinkinį.
    Naudojimas (views.py):
        set = UzklausaBlokuSet.for_instances(uzklausa, uzklausa.detale, request.POST or None)
        if all(f.is_valid() for f in set.all_forms()):
            set.save()
    """
    def __init__(
        self,
        projekto: UzklausosProjektoDuomenysForm,
        kiekiai: KiekiaiTerminaiForm,
        kabinimas: KabinimasRemaiForm,
        pakavimas: PakavimasForm,
        kainodara: KainodaraForm,
        kainos_partijai_fs,  # formset
        ident: DetalesIdentifikacijaForm,
        spec: DetalesSpecifikacijaForm,
        dangos: PavirsiaiDangosForm,
    ):
        self.projekto = projekto
        self.kiekiai = kiekiai
        self.kabinimas = kabinimas
        self.pakavimas = pakavimas
        self.kainodara = kainodara
        self.kainos_partijai_fs = kainos_partijai_fs
        self.ident = ident
        self.spec = spec
        self.dangos = dangos

    @classmethod
    def for_instances(cls, uzklausa: Uzklausa, detale: Detale, data=None, files=None, extra_partiju=3):
        # get_or_create OneToOne „palydovus“
        projekto_obj, _ = UzklausosProjektoDuomenys.objects.get_or_create(uzklausa=uzklausa)
        kiekiai_obj, _ = KiekiaiTerminai.objects.get_or_create(uzklausa=uzklausa)
        kabinimas_obj, _ = KabinimasRemai.objects.get_or_create(uzklausa=uzklausa)
        pakavimas_obj, _ = Pakavimas.objects.get_or_create(uzklausa=uzklausa)
        kainodara_obj, _ = Kainodara.objects.get_or_create(uzklausa=uzklausa)

        ident_obj, _ = DetalesIdentifikacija.objects.get_or_create(detale=detale)
        spec_obj, _ = DetalesSpecifikacija.objects.get_or_create(detale=detale)
        dangos_obj, _ = PavirsiaiDangos.objects.get_or_create(detale=detale)

        projekto = UzklausosProjektoDuomenysForm(data=data, files=files, instance=projekto_obj)
        kiekiai = KiekiaiTerminaiForm(data=data, files=files, instance=kiekiai_obj)
        kabinimas = KabinimasRemaiForm(data=data, files=files, instance=kabinimas_obj)
        pakavimas = PakavimasForm(data=data, files=files, instance=pakavimas_obj)
        kainodara = KainodaraForm(data=data, files=files, instance=kainodara_obj)

        FS = build_kainos_partijai_formset(extra=extra_partiju)
        kainos_fs = FS(data=data, files=files, instance=kainodara_obj, prefix="kainos_partijai")

        ident = DetalesIdentifikacijaForm(data=data, files=files, instance=ident_obj)
        spec = DetalesSpecifikacijaForm(data=data, files=files, instance=spec_obj)
        dangos = PavirsiaiDangosForm(data=data, files=files, instance=dangos_obj)

        return cls(projekto, kiekiai, kabinimas, pakavimas, kainodara, kainos_fs, ident, spec, dangos)

    def all_forms(self):
        return [
            self.projekto, self.kiekiai, self.kabinimas, self.pakavimas,
            self.kainodara, self.ident, self.spec, self.dangos
        ] + list(self.kainos_partijai_fs.forms)

    def is_valid(self):
        return all(f.is_valid() for f in self.all_forms()) and self.kainos_partijai_fs.is_valid()

    def save(self, commit=True):
        objs = []
        objs.append(self.projekto.save(commit))
        objs.append(self.kiekiai.save(commit))
        objs.append(self.kabinimas.save(commit))
        objs.append(self.pakavimas.save(commit))
        kd = self.kainodara.save(commit)
        objs.append(kd)
        # Formset po tėvo išsaugojimo
        self.kainos_partijai_fs.instance = kd
        self.kainos_partijai_fs.save()

        objs.append(self.ident.save(commit))
        objs.append(self.spec.save(commit))
        objs.append(self.dangos.save(commit))
        return objs


# ======== PAPRASTAS FILTRAVIMO FORMOS PAVYZDYS (jei prireiktų sąrašui) ========
class UzklausaFilterForm(forms.Form):
    q = forms.CharField(label=_("Paieška"), required=False, widget=forms.TextInput(attrs=_DEFAULT_INPUT_CSS))
    klientas = forms.ModelChoiceField(
        queryset=Klientas.objects.all(), required=False, widget=forms.Select(attrs=_DEFAULT_INPUT_CSS)
    )
    projektas = forms.ModelChoiceField(
        queryset=Projektas.objects.all(), required=False, widget=forms.Select(attrs=_DEFAULT_INPUT_CSS)
    )
    brezinio_nr = forms.CharField(label=_("Brėžinio nr."), required=False, widget=forms.TextInput(attrs=_DEFAULT_INPUT_CSS))
    metalas = forms.CharField(label=_("Metalas"), required=False, widget=forms.TextInput(attrs=_DEFAULT_INPUT_CSS))
    padengimas = forms.CharField(label=_("Padengimas (KTL/Milt.)"), required=False, widget=forms.TextInput(attrs=_DEFAULT_INPUT_CSS))
