# -*- coding: utf-8 -*-
from decimal import Decimal, InvalidOperation

from django import forms
from django.utils import timezone

from .models import (
    Uzklausa, Kaina, Klientas, Projektas, Detale,
    DetaleSpecifikacija, PavirsiuDangos
)

# Jei turi kainų servisą – naudosime; jei nėra, veiks fallback'as
try:
    from .services import KainosService
except Exception:
    KainosService = None


# --- Pagalbinė konversija kableliui ---
def _to_decimal(val):
    if val in (None, ""):
        return None
    s = str(val).strip().replace(" ", "").replace(",", ".")
    try:
        return Decimal(s)
    except (InvalidOperation, ValueError):
        return None


# === Filtras sąrašui (kaina priima kablelį) ===
class UzklausaFilterForm(forms.Form):
    q = forms.CharField(required=False, label="Paieška")
    klientas = forms.ModelChoiceField(queryset=Klientas.objects.all(), required=False, label="Klientas")
    projektas = forms.ModelChoiceField(queryset=Projektas.objects.all(), required=False, label="Projektas")
    detale = forms.ModelChoiceField(queryset=Detale.objects.all(), required=False, label="Detalė")
    brezinio_nr = forms.CharField(required=False, label="Brėžinio Nr.")
    metalas = forms.CharField(required=False, label="Metalas")
    padengimas = forms.CharField(required=False, label="Padengimas")

    kaina_nuo = forms.CharField(required=False, label="Kaina nuo (€)")
    kaina_iki = forms.CharField(required=False, label="Kaina iki (€)")

    def clean(self):
        cleaned = super().clean()
        for name in ("kaina_nuo", "kaina_iki"):
            val = _to_decimal(cleaned.get(name))
            if cleaned.get(name) not in (None, "") and val is None:
                self.add_error(name, "Įveskite teisingą skaičių (pvz., 2,70 arba 2.70).")
            cleaned[name] = val
        return cleaned


# === Užklausos sukūrimas / pasirinkimas (atitinka tavo create šabloną) ===
class UzklausaCreateOrSelectForm(forms.ModelForm):
    # Esami
    klientas = forms.ModelChoiceField(queryset=Klientas.objects.all(), required=False, label="Esamas klientas")
    projektas = forms.ModelChoiceField(queryset=Projektas.objects.all(), required=False, label="Esamas projektas")
    detale = forms.ModelChoiceField(queryset=Detale.objects.all(), required=False, label="Esama detalė")

    # Nauji (tekstu)
    naujas_klientas = forms.CharField(required=False, label="Naujas klientas")
    naujas_projektas = forms.CharField(required=False, label="Naujas projektas")
    detales_pavadinimas = forms.CharField(required=False, label="Nauja detalė – pavadinimas")
    brezinio_nr = forms.CharField(required=False, label="Brėžinio nr.")

    # Specifikacija
    metalas = forms.CharField(required=False, label="Metalas")
    plotas_m2 = forms.CharField(required=False, label="Plotas m²")
    svoris_kg = forms.CharField(required=False, label="Svoris kg")
    medziagos_kodas = forms.CharField(required=False, label="Medžiagos kodas")

    # Dangos
    ktl_ec_name = forms.CharField(required=False, label="KTL / e-coating")
    miltelinis_name = forms.CharField(required=False, label="Miltelinis padengimas")
    spalva_ral = forms.CharField(required=False, label="RAL / spalva")
    blizgumas = forms.CharField(required=False, label="Blizgumas / tekstūra")

    # Pradinė kaina
    kaina_suma = forms.CharField(required=False, label="Kaina")
    kaina_valiuta = forms.CharField(required=False, initial="EUR", label="Valiuta")
    kaina_priezastis = forms.CharField(required=False, label="Priežastis")

    class Meta:
        model = Uzklausa
        fields = "__all__"

    def clean(self):
        cleaned = super().clean()
        # Bent vienas iš dviejų (esamas | naujas)
        if not cleaned.get("klientas") and not cleaned.get("naujas_klientas"):
            self.add_error("klientas", "Pasirinkite esamą arba įveskite naują klientą.")
        if not cleaned.get("projektas") and not cleaned.get("naujas_projektas"):
            self.add_error("projektas", "Pasirinkite esamą arba įveskite naują projektą.")
        if not cleaned.get("detale") and not cleaned.get("detales_pavadinimas") and not cleaned.get("brezinio_nr"):
            self.add_error("detale", "Pasirinkite esamą detalę arba įveskite naują.")

        for name in ("plotas_m2", "svoris_kg", "kaina_suma"):
            val = _to_decimal(cleaned.get(name))
            if cleaned.get(name) not in (None, "") and val is None:
                self.add_error(name, "Įveskite teisingą skaičių (pvz., 2,70 arba 2.70).")
            cleaned[name] = val

        cleaned["kaina_valiuta"] = "EUR"
        return cleaned

    def save(self, commit=True):
        # 1) Klientas
        klientas = self.cleaned_data.get("klientas")
        if not klientas:
            klientas, _ = Klientas.objects.get_or_create(
                vardas=(self.cleaned_data.get("naujas_klientas") or "").strip()
            )

        # 2) Projektas (būtina pririšti prie kliento)
        projektas = self.cleaned_data.get("projektas")
        if not projektas:
            projektas, _ = Projektas.objects.get_or_create(
                klientas=klientas,
                pavadinimas=(self.cleaned_data.get("naujas_projektas") or "").strip() or "",
            )

        # 3) Detalė (pririšta prie projekto)
        detale = self.cleaned_data.get("detale")
        if not detale:
            detale = Detale.objects.create(
                projektas=projektas,
                pavadinimas=(self.cleaned_data.get("detales_pavadinimas") or "").strip() or "",
                brezinio_nr=(self.cleaned_data.get("brezinio_nr") or "").strip() or "",
            )

        # 4) Specifikacija
        metalas = (self.cleaned_data.get("metalas") or "").strip()
        plotas_m2 = self.cleaned_data.get("plotas_m2")
        svoris_kg = self.cleaned_data.get("svoris_kg")
        medziagos_kodas = (self.cleaned_data.get("medziagos_kodas") or "").strip()
        if any([metalas, plotas_m2 is not None, svoris_kg is not None, medziagos_kodas]):
            spec = getattr(detale, "specifikacija", None) or DetaleSpecifikacija(detale=detale)
            if metalas: spec.metalas = metalas
            if plotas_m2 is not None: spec.plotas_m2 = plotas_m2
            if svoris_kg is not None: spec.svoris_kg = svoris_kg
            if medziagos_kodas: spec.medziagos_kodas = medziagos_kodas
            spec.save()

        # 5) Dangos
        ktl = (self.cleaned_data.get("ktl_ec_name") or "").strip()
        milt = (self.cleaned_data.get("miltelinis_name") or "").strip()
        ral = (self.cleaned_data.get("spalva_ral") or "").strip()
        blizg = (self.cleaned_data.get("blizgumas") or "").strip()
        if any([ktl, milt, ral, blizg]):
            dang = getattr(detale, "pavirsiu_dangos", None) or PavirsiuDangos(detale=detale)
            if ktl: dang.ktl_ec_name = ktl
            if milt: dang.miltelinis_name = milt
            if ral: dang.spalva_ral = ral
            if blizg: dang.blizgumas = blizg
            dang.save()

        # 6) Užklausa
        self.instance.klientas = klientas
        self.instance.projektas = projektas
        self.instance.detale = detale
        uzk = super().save(commit=commit)

        # 7) Pradinė kaina
        suma = self.cleaned_data.get("kaina_suma")
        priezastis = (self.cleaned_data.get("kaina_priezastis") or "").strip()
        if suma is not None:
            if KainosService:
                KainosService.nustatyti_nauja_kaina(
                    uzklausa_id=uzk.id,
                    detale_id=None,
                    suma=suma,
                    valiuta="EUR",
                    priezastis=priezastis,
                    user=getattr(self, "user", None),
                )
            else:
                Kaina.objects.filter(uzklausa=uzk, yra_aktuali=True).update(
                    yra_aktuali=False, galioja_iki=timezone.now()
                )
                Kaina.objects.create(
                    uzklausa=uzk, suma=suma, valiuta="EUR",
                    yra_aktuali=True, galioja_nuo=timezone.now(),
                    keitimo_priezastis=priezastis, pakeite=getattr(self, "user", None),
                )
        return uzk


# === Užklausos redagavimas (atitinka tavo edit šabloną) ===
class UzklausaEditForm(forms.ModelForm):
    # Pagrindiniai ryšiai
    klientas = forms.ModelChoiceField(queryset=Klientas.objects.all(), required=False, label="Klientas")
    projektas = forms.ModelChoiceField(queryset=Projektas.objects.all(), required=False, label="Projektas")
    detale = forms.ModelChoiceField(queryset=Detale.objects.all(), required=False, label="Detalė")

    # Detalės bazė
    detale_pavadinimas = forms.CharField(required=False, label="Detalės pavadinimas")
    detale_brezinio_nr = forms.CharField(required=False, label="Brėžinio nr.")

    # Kiekiai
    kiekis_metinis = forms.IntegerField(required=False, label="Kiekis per metus")
    kiekis_menesis = forms.IntegerField(required=False, label="Kiekis per mėnesį")
    kiekis_partijai = forms.IntegerField(required=False, label="Kiekis partijai")
    kiekis_per_val = forms.IntegerField(required=False, label="Gaminių/val.")

    # Matmenys (su kableliu)
    ilgis_mm = forms.CharField(required=False, label="Ilgis (mm)")
    plotis_mm = forms.CharField(required=False, label="Plotis (mm)")
    aukstis_mm = forms.CharField(required=False, label="Aukštis (mm)")
    skersmuo_mm = forms.CharField(required=False, label="Skersmuo (mm)")
    storis_mm = forms.CharField(required=False, label="Storis (mm)")

    # Specifikacija
    metalas = forms.CharField(required=False, label="Metalas")
    plotas_m2 = forms.CharField(required=False, label="Plotas m²")
    svoris_kg = forms.CharField(required=False, label="Svoris kg")
    medziagos_kodas = forms.CharField(required=False, label="Medžiagos kodas")

    # Dangos
    ktl_ec_name = forms.CharField(required=False, label="KTL / e-coating")
    miltelinis_name = forms.CharField(required=False, label="Miltelinis padengimas")
    spalva_ral = forms.CharField(required=False, label="RAL / spalva")
    blizgumas = forms.CharField(required=False, label="Blizgumas / tekstūra")

    # Kabinimas
    kabinimo_budas = forms.CharField(required=False, label="Kabinimo būdas")
    kabliuku_kiekis = forms.IntegerField(required=False, label="Kabliukų kiekis")
    kabinimo_anga_mm = forms.CharField(required=False, label="Kabinimo anga (mm)")
    kabinti_per = forms.CharField(required=False, label="Kabinti per")

    # Pakuotė
    pakuotes_tipas = forms.CharField(required=False, label="Pakuotės tipas")
    vienetai_dezeje = forms.IntegerField(required=False, label="Vnt/dėžėje")
    vienetai_paleje = forms.IntegerField(required=False, label="Vnt/palėje")
    pakuotes_pastabos = forms.CharField(required=False, label="Spec. žymėjimas")

    # Testai
    testai_druskos_rukas_val = forms.IntegerField(required=False, label="Druskos rūkas (val.)")
    testas_adhezija = forms.CharField(required=False, label="Adhezijos testas")
    testas_storis_mikronai = forms.IntegerField(required=False, label="Storis (µm)")
    testai_kita = forms.CharField(required=False, label="Kiti reikalavimai")

    # Dokumentai / Pastabos
    projekto_aprasymas = forms.CharField(required=False, label="Projekto aprašymas", widget=forms.Textarea)
    uzklausos_pastabos = forms.CharField(required=False, label="Užklausos pastabos", widget=forms.Textarea)

    # Kaina (mini)
    kaina_suma = forms.CharField(required=False, label="Nauja kaina (€)")
    kaina_valiuta = forms.CharField(required=False, initial="EUR", label="Valiuta")
    kaina_priezastis = forms.CharField(required=False, label="Keitimo priežastis")

    class Meta:
        model = Uzklausa
        fields = "__all__"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        uzk = self.instance
        det = getattr(uzk, "detale", None)
        proj = getattr(uzk, "projektas", None)

        # Detalės bazė + kiekiai/matmenys/kabinimas/pakuotė/testai
        if det:
            self.fields["detale_pavadinimas"].initial = det.pavadinimas or ""
            self.fields["detale_brezinio_nr"].initial = det.brezinio_nr or ""
            for name in (
                "kiekis_metinis", "kiekis_menesis", "kiekis_partijai", "kiekis_per_val",
                "ilgis_mm", "plotis_mm", "aukstis_mm", "skersmuo_mm", "storis_mm",
                "kabinimo_budas", "kabliuku_kiekis", "kabinimo_anga_mm", "kabinti_per",
                "pakuotes_tipas", "vienetai_dezeje", "vienetai_paleje", "pakuotes_pastabos",
                "testai_druskos_rukas_val", "testas_adhezija", "testas_storis_mikronai", "testai_kita"
            ):
                if hasattr(det, name):
                    self.fields[name].initial = getattr(det, name)

            # Specifikacija
            spec = getattr(det, "specifikacija", None)
            if spec:
                self.fields["metalas"].initial = spec.metalas or ""
                self.fields["plotas_m2"].initial = spec.plotas_m2
                self.fields["svoris_kg"].initial = spec.svoris_kg
                self.fields["medziagos_kodas"].initial = spec.medziagos_kodas or ""

            # Dangos
            dang = getattr(det, "pavirsiu_dangos", None)
            if dang:
                self.fields["ktl_ec_name"].initial = dang.ktl_ec_name or ""
                self.fields["miltelinis_name"].initial = dang.miltelinis_name or ""
                self.fields["spalva_ral"].initial = dang.spalva_ral or ""
                self.fields["blizgumas"].initial = dang.blizgumas or ""

        # Projektas / Užklausa
        if proj:
            self.fields["projekto_aprasymas"].initial = proj.aprasymas or ""
        self.fields["uzklausos_pastabos"].initial = uzk.pastabos or ""

        # Valiuta – visada EUR
        self.fields["kaina_valiuta"].initial = "EUR"

    def clean(self):
        cleaned = super().clean()
        # Decimal laukai (priimame kablelį)
        for name in (
            "ilgis_mm", "plotis_mm", "aukstis_mm", "skersmuo_mm", "storis_mm",
            "kabinimo_anga_mm", "plotas_m2", "svoris_kg", "kaina_suma"
        ):
            val = _to_decimal(cleaned.get(name))
            if cleaned.get(name) not in (None, "") and val is None:
                self.add_error(name, "Įveskite teisingą skaičių (pvz., 2,70 arba 2.70).")
            cleaned[name] = val

        cleaned["pastabos"] = cleaned.get("uzklausos_pastabos") or None
        cleaned["kaina_valiuta"] = "EUR"
        return cleaned

    def save(self, commit=True):
        uzk = self.instance
        det = uzk.detale
        proj = uzk.projektas

        klientas = self.cleaned_data.get("klientas") or uzk.klientas
        projektas = self.cleaned_data.get("projektas") or proj
        detale = self.cleaned_data.get("detale") or det

        # Projekto aprašymas
        proj_desc = self.cleaned_data.get("projekto_aprasymas")
        if projektas and proj_desc is not None:
            projektas.aprasymas = proj_desc
            projektas.save(update_fields=["aprasymas"])

        # Detalės projektas
        if detale and projektas and detale.projektas_id != projektas.id:
            detale.projektas = projektas
            detale.save(update_fields=["projektas"])

        # Atnaujinam Detalę
        if detale:
            base_map = {
                "pavadinimas": self.cleaned_data.get("detale_pavadinimas"),
                "brezinio_nr": self.cleaned_data.get("detale_brezinio_nr"),
                "kiekis_metinis": self.cleaned_data.get("kiekis_metinis"),
                "kiekis_menesis": self.cleaned_data.get("kiekis_menesis"),
                "kiekis_partijai": self.cleaned_data.get("kiekis_partijai"),
                "kiekis_per_val": self.cleaned_data.get("kiekis_per_val"),
                "ilgis_mm": self.cleaned_data.get("ilgis_mm"),
                "plotis_mm": self.cleaned_data.get("plotis_mm"),
                "aukstis_mm": self.cleaned_data.get("aukstis_mm"),
                "skersmuo_mm": self.cleaned_data.get("skersmuo_mm"),
                "storis_mm": self.cleaned_data.get("storis_mm"),
                "kabinimo_budas": self.cleaned_data.get("kabinimo_budas"),
                "kabliuku_kiekis": self.cleaned_data.get("kabliuku_kiekis"),
                "kabinimo_anga_mm": self.cleaned_data.get("kabinimo_anga_mm"),
                "kabinti_per": self.cleaned_data.get("kabinti_per"),
                "pakuotes_tipas": self.cleaned_data.get("pakuotes_tipas"),
                "vienetai_dezeje": self.cleaned_data.get("vienetai_dezeje"),
                "vienetai_paleje": self.cleaned_data.get("vienetai_paleje"),
                "pakuotes_pastabos": self.cleaned_data.get("pakuotes_pastabos"),
                "testai_druskos_rukas_val": self.cleaned_data.get("testai_druskos_rukas_val"),
                "testas_adhezija": self.cleaned_data.get("testas_adhezija"),
                "testas_storis_mikronai": self.cleaned_data.get("testas_storis_mikronai"),
                "testai_kita": self.cleaned_data.get("testai_kita"),
            }
            for f, v in base_map.items():
                if v is not None:
                    setattr(detale, f, v)
            detale.save()

            # Specifikacija
            spec = getattr(detale, "specifikacija", None) or DetaleSpecifikacija(detale=detale)
            spec_map = {
                "metalas": self.cleaned_data.get("metalas"),
                "plotas_m2": self.cleaned_data.get("plotas_m2"),
                "svoris_kg": self.cleaned_data.get("svoris_kg"),
                "medziagos_kodas": self.cleaned_data.get("medziagos_kodas"),
            }
            for f, v in spec_map.items():
                if v not in (None, ""):
                    setattr(spec, f, v)
            spec.save()

            # Dangos
            dang = getattr(detale, "pavirsiu_dangos", None) or PavirsiuDangos(detale=detale)
            dang_map = {
                "ktl_ec_name": self.cleaned_data.get("ktl_ec_name"),
                "miltelinis_name": self.cleaned_data.get("miltelinis_name"),
                "spalva_ral": self.cleaned_data.get("spalva_ral"),
                "blizgumas": self.cleaned_data.get("blizgumas"),
            }
            for f, v in dang_map.items():
                if v not in (None, ""):
                    setattr(dang, f, v)
            dang.save()

        # Uzklausa
        uzk.klientas = klientas
        uzk.projektas = projektas
        uzk.detale = detale
        uzk.pastabos = self.cleaned_data.get("pastabos")
        uzk = super().save(commit=commit)

        # Mini kaina
        suma = self.cleaned_data.get("kaina_suma")
        priezastis = (self.cleaned_data.get("kaina_priezastis") or "").strip()
        if suma is not None:
            if KainosService:
                KainosService.nustatyti_nauja_kaina(
                    uzklausa_id=uzk.id,
                    detale_id=None,
                    suma=suma,
                    valiuta="EUR",
                    priezastis=priezastis,
                    user=getattr(self, "user", None),
                )
            else:
                Kaina.objects.filter(uzklausa=uzk, yra_aktuali=True).update(
                    yra_aktuali=False, galioja_iki=timezone.now()
                )
                Kaina.objects.create(
                    uzklausa=uzk, suma=suma, valiuta="EUR",
                    yra_aktuali=True, galioja_nuo=timezone.now(),
                    keitimo_priezastis=priezastis, pakeite=getattr(self, "user", None),
                )
        return uzk


# === CSV importas ===
class ImportUzklausosCSVForm(forms.Form):
    file = forms.FileField(required=True, label="CSV failas")


# === Kaina (inline formset/re-use) – valiuta slepiama, fiksuojama EUR ===
class KainaForm(forms.ModelForm):
    class Meta:
        model = Kaina
        fields = "__all__"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if "valiuta" in self.fields:
            self.fields["valiuta"].widget = forms.HiddenInput()
            if not getattr(self.instance, "pk", None):
                self.fields["valiuta"].initial = "EUR"

    def clean(self):
        data = super().clean()
        data["valiuta"] = "EUR"
        return data

    def save(self, commit=True):
        obj = super().save(commit=False)
        obj.valiuta = "EUR"
        if hasattr(obj, "galioja_nuo") and not getattr(obj, "galioja_nuo", None):
            obj.galioja_nuo = timezone.now()
        if commit:
            obj.save()
        return obj


# === „Mini“ kaina forma (naudojama atskirai) ===
class KainaRedagavimoForm(forms.Form):
    suma = forms.CharField(required=True, label="Suma (€)")
    valiuta = forms.CharField(required=False, initial="EUR", label="Valiuta")
    keitimo_priezastis = forms.CharField(required=False, label="Priežastis")

    def clean_suma(self):
        raw = self.cleaned_data.get("suma")
        val = _to_decimal(raw)
        if val is None:
            raise forms.ValidationError("Įveskite teisingą sumą (pvz., 2,70 arba 2.70).")
        return val

    def clean_valiuta(self):
        return "EUR"
