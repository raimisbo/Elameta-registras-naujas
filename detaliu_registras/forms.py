from django import forms
from django.core.exceptions import ValidationError
from django.apps import apps
from django.db.models.manager import BaseManager
from django.utils import timezone

from .models import Uzklausa, Klientas, Projektas, Detale, Kaina


# === Filtrų forma (sąrašui) ===
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


# === CSV importas (stub) ===
class ImportUzklausosCSVForm(forms.Form):
    file = forms.FileField(label="Pasirinkite CSV failą")


# === Nauja užklausa: pasirink arba sukurk vietoje ===
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

    # Specifikacija
    metalas = forms.CharField(label="Metalas", required=False)
    plotas_m2 = forms.DecimalField(label="Plotas m²", required=False, decimal_places=4, max_digits=12)
    svoris_kg = forms.DecimalField(label="Svoris kg", required=False, decimal_places=4, max_digits=12)
    medziagos_kodas = forms.CharField(label="Medžiagos kodas", required=False)

    # Dangos
    ktl_ec_name = forms.CharField(label="KTL / e-coating", required=False)
    miltelinis_name = forms.CharField(label="Miltelinis padengimas", required=False)
    spalva_ral = forms.CharField(label="RAL / spalva", required=False)
    blizgumas = forms.CharField(label="Blizgumas / tekstūra", required=False)

    class Meta:
        model = Uzklausa
        fields = []  # viską kuriame save() metu

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
            klientas = Klientas.objects.create(vardas=(c.get("naujas_klientas") or "").strip())

        # Projektas
        projektas = c.get("projektas")
        if not projektas:
            projektas = Projektas.objects.create(
                pavadinimas=(c.get("naujas_projektas") or "").strip(),
                klientas=klientas,
            )

        # Detalė
        detale = c.get("detale")
        if not detale:
            detale = Detale.objects.create(
                pavadinimas=c.get("detales_pavadinimas") or "Be pavadinimo",
                brezinio_nr=c.get("brezinio_nr") or "",
                projektas=projektas,  # ⬅ svarbu: pririšti prie projekto
            )

        # Specifikacija
        if any([c.get("metalas"), c.get("plotas_m2") is not None, c.get("svoris_kg") is not None, c.get("medziagos_kodas")]):
            DetaleSpecifikacija = apps.get_model("detaliu_registras", "DetaleSpecifikacija")
            if DetaleSpecifikacija:
                spec, _ = DetaleSpecifikacija.objects.get_or_create(detale=detale)
                if c.get("metalas"): spec.metalas = c["metalas"].strip()
                if c.get("plotas_m2") is not None: spec.plotas_m2 = c["plotas_m2"]
                if c.get("svoris_kg") is not None: spec.svoris_kg = c["svoris_kg"]
                if c.get("medziagos_kodas"): spec.medziagos_kodas = c["medziagos_kodas"].strip()
                spec.save()

        # Dangos
        if any([c.get("ktl_ec_name"), c.get("miltelinis_name"), c.get("spalva_ral"), c.get("blizgumas")]):
            PavirsiuDangos = apps.get_model("detaliu_registras", "PavirsiuDangos")
            if PavirsiuDangos:
                pd, _ = PavirsiuDangos.objects.get_or_create(detale=detale)
                if c.get("ktl_ec_name"): pd.ktl_ec_name = c["ktl_ec_name"].strip()
                if c.get("miltelinis_name"): pd.miltelinis_name = c["miltelinis_name"].strip()
                if c.get("spalva_ral"): pd.spalva_ral = c["spalva_ral"].strip()
                if c.get("blizgumas"): pd.blizgumas = c["blizgumas"].strip()
                pd.save()

        uzk = Uzklausa(klientas=klientas, projektas=projektas, detale=detale)
        if commit:
            uzk.save()
        return uzk


# === REDAGAVIMAS: 9 blokų forma ===
class UzklausaEditForm(forms.ModelForm):
    # Pagrindinė
    klientas = forms.ModelChoiceField(
        label="Klientas", queryset=Klientas.objects.all().order_by("vardas"), required=False
    )
    projektas = forms.ModelChoiceField(
        label="Projektas", queryset=Projektas.objects.all().order_by("pavadinimas"), required=False
    )
    detale = forms.ModelChoiceField(
        label="Detalė", queryset=Detale.objects.all().order_by("pavadinimas"), required=False
    )

    # Detalės bazė
    detale_pavadinimas = forms.CharField(label="Detalės pavadinimas", required=False)
    detale_brezinio_nr = forms.CharField(label="Brėžinio nr.", required=False)

    # Kiekiai
    kiekis_metinis = forms.IntegerField(label="Kiekis per metus", required=False)
    kiekis_menesis = forms.IntegerField(label="Kiekis per mėnesį", required=False)
    kiekis_partijai = forms.IntegerField(label="Kiekis partijai", required=False)
    kiekis_per_val = forms.IntegerField(label="Gaminių/val.", required=False)

    # Matmenys
    ilgis_mm = forms.DecimalField(label="Ilgis (mm)", required=False, decimal_places=2, max_digits=12)
    plotis_mm = forms.DecimalField(label="Plotis (mm)", required=False, decimal_places=2, max_digits=12)
    aukstis_mm = forms.DecimalField(label="Aukštis (mm)", required=False, decimal_places=2, max_digits=12)
    skersmuo_mm = forms.DecimalField(label="Skersmuo (mm)", required=False, decimal_places=2, max_digits=12)
    storis_mm = forms.DecimalField(label="Storis (mm)", required=False, decimal_places=2, max_digits=12)

    # Specifikacija
    metalas = forms.CharField(label="Metalas", required=False)
    plotas_m2 = forms.DecimalField(label="Plotas m²", required=False, decimal_places=4, max_digits=12)
    svoris_kg = forms.DecimalField(label="Svoris kg", required=False, decimal_places=4, max_digits=12)
    medziagos_kodas = forms.CharField(label="Medžiagos kodas", required=False)

    # Dangos
    ktl_ec_name = forms.CharField(label="KTL / e-coating", required=False)
    miltelinis_name = forms.CharField(label="Miltelinis padengimas", required=False)
    spalva_ral = forms.CharField(label="RAL / spalva", required=False)
    blizgumas = forms.CharField(label="Blizgumas / tekstūra", required=False)

    # Kabinimas
    kabinimo_budas = forms.CharField(label="Kabinimo būdas", required=False)
    kabliuku_kiekis = forms.IntegerField(label="Kabliukų kiekis", required=False)
    kabinimo_anga_mm = forms.DecimalField(label="Kabinimo anga (mm)", required=False, decimal_places=2, max_digits=12)
    kabinti_per = forms.CharField(label="Kabinti per", required=False)

    # Pakuotė
    pakuotes_tipas = forms.CharField(label="Pakuotės tipas", required=False)
    vienetai_dezeje = forms.IntegerField(label="Vnt/dėžėje", required=False)
    vienetai_paleje = forms.IntegerField(label="Vnt/palėje", required=False)
    pakuotes_pastabos = forms.CharField(label="Spec. žymėjimas", required=False)

    # Testai / Kokybė
    testai_druskos_rukas_val = forms.IntegerField(label="Druskos rūkas (val.)", required=False)
    testas_adhezija = forms.CharField(label="Adhezijos testas", required=False)
    testas_storis_mikronai = forms.IntegerField(label="Storis (µm)", required=False)
    testai_kita = forms.CharField(label="Kiti reikalavimai", required=False)

    # Dokumentai / Pastabos
    projekto_aprasymas = forms.CharField(label="Projekto aprašymas", required=False)
    uzklausos_pastabos = forms.CharField(label="Užklausos pastabos", required=False)

    class Meta:
        model = Uzklausa
        fields = []  # valdome ranka

    def _has_concrete_field(self, instance, field_name: str) -> bool:
        names = [f.name for f in instance._meta.get_fields() if getattr(f, "concrete", False)]
        return field_name in names

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        u: Uzklausa = kwargs.get("instance")
        if not u:
            return

        # ryšiai
        if "klientas" in self.fields:
            self.fields["klientas"].initial = getattr(u, "klientas", None)
        if "projektas" in self.fields:
            self.fields["projektas"].initial = getattr(u, "projektas", None)
        if "detale" in self.fields:
            self.fields["detale"].initial = getattr(u, "detale", None)

        d = getattr(u, "detale", None)
        if d:
            # bazė
            if "detale_pavadinimas" in self.fields:
                self.fields["detale_pavadinimas"].initial = getattr(d, "pavadinimas", "")
            if "detale_brezinio_nr" in self.fields:
                self.fields["detale_brezinio_nr"].initial = getattr(d, "brezinio_nr", "")

            # paprasti Detale laukai
            for fname in [
                "kiekis_metinis","kiekis_menesis","kiekis_partijai","kiekis_per_val",
                "ilgis_mm","plotis_mm","aukstis_mm","skersmuo_mm","storis_mm",
                "kabinimo_budas","kabliuku_kiekis","kabinimo_anga_mm","kabinti_per",
                "pakuotes_tipas","vienetai_dezeje","vienetai_paleje","pakuotes_pastabos",
                "testai_druskos_rukas_val","testas_adhezija","testas_storis_mikronai","testai_kita",
                "ppap_dokumentai","priedai_info",
            ]:
                if fname in self.fields and hasattr(d, fname):
                    self.fields[fname].initial = getattr(d, fname)

            # specifikacija
            spec = getattr(d, "specifikacija", None)
            if spec:
                for fname in ["metalas","plotas_m2","svoris_kg","medziagos_kodas"]:
                    if fname in self.fields and hasattr(spec, fname):
                        self.fields[fname].initial = getattr(spec, fname)

            # dangos
            coats = getattr(d, "pavirsiu_dangos", None)
            if coats:
                for fname in ["ktl_ec_name","miltelinis_name","spalva_ral","blizgumas"]:
                    if fname in self.fields and hasattr(coats, fname):
                        self.fields[fname].initial = getattr(coats, fname)

        # projekto aprašymas
        p = getattr(u, "projektas", None)
        if p and hasattr(p, "aprasymas") and "projekto_aprasymas" in self.fields:
            self.fields["projekto_aprasymas"].initial = getattr(p, "aprasymas")

        # užklausos pastabos (tik jei modelyje yra konkretus laukas)
        if "uzklausos_pastabos" in self.fields and self._has_concrete_field(u, "pastabos"):
            val = getattr(u, "pastabos", None)
            if not isinstance(val, BaseManager):
                self.fields["uzklausos_pastabos"].initial = val
        else:
            self.fields.pop("uzklausos_pastabos", None)

    def save(self, commit=True):
        u: Uzklausa = self.instance
        c = self.cleaned_data

        # ryšiai
        if "klientas" in c and c.get("klientas"):
            u.klientas = c["klientas"]
        if "projektas" in c and c.get("projektas"):
            u.projektas = c["projektas"]
        if "detale" in c and c.get("detale"):
            u.detale = c["detale"]

        d = getattr(u, "detale", None)
        if d:
            # bazė
            if "detale_pavadinimas" in c and hasattr(d, "pavadinimas"):
                d.pavadinimas = c["detale_pavadinimas"] or d.pavadinimas
            if "detale_brezinio_nr" in c and hasattr(d, "brezinio_nr"):
                d.brezinio_nr = c["detale_brezinio_nr"]

            # paprasti Detale laukai
            simple_map = {
                "kiekis_metinis": int, "kiekis_menesis": int, "kiekis_partijai": int, "kiekis_per_val": int,
                "ilgis_mm": float, "plotis_mm": float, "aukstis_mm": float, "skersmuo_mm": float, "storis_mm": float,
                "kabinimo_budas": str, "kabliuku_kiekis": int, "kabinimo_anga_mm": float, "kabinti_per": str,
                "pakuotes_tipas": str, "vienetai_dezeje": int, "vienetai_paleje": int, "pakuotes_pastabos": str,
                "testai_druskos_rukas_val": int, "testas_adhezija": str, "testas_storis_mikronai": int, "testai_kita": str,
                "ppap_dokumentai": str, "priedai_info": str,
            }
            for fname, _ in simple_map.items():
                if fname in c and c.get(fname) is not None and hasattr(d, fname):
                    setattr(d, fname, c[fname])

            # specifikacija
            if any(c.get(x) not in [None, ""] for x in ["metalas","plotas_m2","svoris_kg","medziagos_kodas"]):
                DetaleSpecifikacija = apps.get_model("detaliu_registras", "DetaleSpecifikacija")
                if DetaleSpecifikacija:
                    spec = getattr(d, "specifikacija", None)
                    if not spec:
                        spec, _ = DetaleSpecifikacija.objects.get_or_create(detale=d)
                    for fname in ["metalas","plotas_m2","svoris_kg","medziagos_kodas"]:
                        if fname in c and hasattr(spec, fname) and c.get(fname) is not None:
                            setattr(spec, fname, c[fname])
                    spec.save()

            # dangos
            if any(c.get(x) not in [None, ""] for x in ["ktl_ec_name","miltelinis_name","spalva_ral","blizgumas"]):
                PavirsiuDangos = apps.get_model("detaliu_registras", "PavirsiuDangos")
                if PavirsiuDangos:
                    coats = getattr(d, "pavirsiu_dangos", None)
                    if not coats:
                        coats, _ = PavirsiuDangos.objects.get_or_create(detale=d)
                    for fname in ["ktl_ec_name","miltelinis_name","spalva_ral","blizgumas"]:
                        if fname in c and hasattr(coats, fname) and c.get(fname) is not None:
                            setattr(coats, fname, c[fname])
                    coats.save()

            if commit:
                d.save()

        # projekto aprašymas
        if "projekto_aprasymas" in c:
            p = getattr(u, "projektas", None)
            if p and hasattr(p, "aprasymas"):
                p.aprasymas = c["projekto_aprasymas"]
                if commit:
                    p.save()

        # užklausos pastabos
        if "uzklausos_pastabos" in c and self._has_concrete_field(u, "pastabos"):
            val = getattr(u, "pastabos", None)
            if not isinstance(val, BaseManager):
                setattr(u, "pastabos", c["uzklausos_pastabos"])

        if commit:
            u.save()
        return u


class KainaRedagavimoForm(forms.Form):
    suma = forms.DecimalField(label="Kaina", max_digits=12, decimal_places=2, min_value=0)
    valiuta = forms.CharField(label="Valiuta", max_length=3, initial="EUR")
    keitimo_priezastis = forms.CharField(label="Keitimo priežastis", widget=forms.Textarea, required=False)


# --- KAINA: pažangios kainodaros forma (be 'busena') ---
class KainaForm(forms.ModelForm):
    class Meta:
        model = Kaina
        fields = [
            "suma",
            "valiuta",
            "yra_fiksuota",
            "kiekis_nuo",
            "kiekis_iki",
            "fiksuotas_kiekis",
            "kainos_matas",
            "keitimo_priezastis",
        ]
        widgets = {
            "suma": forms.NumberInput(attrs={"step": "0.01"}),
        }

    def clean(self):
        c = super().clean()
        yra_fiksuota = c.get("yra_fiksuota") is True
        kiekis_nuo = c.get("kiekis_nuo")
        kiekis_iki = c.get("kiekis_iki")
        fiksuotas_kiekis = c.get("fiksuotas_kiekis")
        matas = c.get("kainos_matas")

        if yra_fiksuota:
            if not fiksuotas_kiekis:
                raise ValidationError("Pažymėjus 'Yra fiksuota', privalomas 'Fiksuotas kiekis'.")
            if not matas:
                raise ValidationError("Pažymėjus 'Yra fiksuota', privalomas 'Kainos matas'.")
            c["kiekis_nuo"] = None
            c["kiekis_iki"] = None
        else:
            if kiekis_nuo is None and kiekis_iki is None and fiksuotas_kiekis is None:
                raise ValidationError("Nurodykite kiekio intervalą (bent 'Kiekis nuo') arba pažymėkite 'Yra fiksuota'.")
            if kiekis_nuo is not None and kiekis_iki is not None and kiekis_nuo > kiekis_iki:
                raise ValidationError("'Kiekis nuo' negali būti didesnis už 'Kiekis iki'.")
            c["fiksuotas_kiekis"] = None  # intervalinei kainai netaikoma

        return c

    def save(self, commit=True):
        inst: Kaina = super().save(commit=False)
        # žymim kaip aktualią; senoji „aktuali“ bus uždaroma per service/unikalų constraint
        inst.yra_aktuali = True
        if not inst.galioja_nuo:
            inst.galioja_nuo = timezone.now().date()
        if commit:
            inst.save()
        return inst
