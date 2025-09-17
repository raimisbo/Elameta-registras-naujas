# detaliu_registras/views.py
from __future__ import annotations

from django.shortcuts import render, redirect, get_object_or_404
from django.views import View
from django.views.generic import DetailView, ListView
from django.urls import reverse, reverse_lazy
from django.contrib import messages
from django.db import transaction
from django.db.models import Q, Prefetch

from .models import (
    Klientas, Projektas, Detale, Uzklausa,
    UzklausosProjektoDuomenys, KiekiaiTerminai, KabinimasRemai,
    Pakavimas, Kainodara, KainosPartijai,
    DetalesIdentifikacija, DetalesSpecifikacija, PavirsiaiDangos,
)
from .forms import (
    KlientasForm, ProjektasForm, DetaleForm, UzklausaForm,
    UzklausosProjektoDuomenysForm, KiekiaiTerminaiForm, KabinimasRemaiForm,
    PakavimasForm, KainodaraForm, build_kainos_partijai_formset,
    DetalesIdentifikacijaForm, DetalesSpecifikacijaForm, PavirsiaiDangosForm,
    UzklausaFilterForm, UzklausaBlokuSet
)


# ========= Pagalbinės funkcijos =========
def _success_url_for(uzklausa: Uzklausa) -> str:
    return reverse("detaliu_registras:perziureti_uzklausa", args=[uzklausa.pk])


def _context_base():
    """Bendra vieta, jei norėsi paduoti bendrą kontekstą (pvz., breadcrumbs)."""
    return {}


# ========= CREATE =========
class UzklausaCreateView(View):
    template_name = "detaliu_registras/ivesti_uzklausa.html"
    success_message = "Užklausa sėkmingai sukurta."

    def get(self, request, *args, **kwargs):
        ctx = _context_base()
        ctx["uzklausa_form"] = UzklausaForm()
        # Pagrindinių formų „starteriai“, kol nepasirinkta detale/uzklausa
        ctx["projekto_form"] = UzklausosProjektoDuomenysForm()
        ctx["kiekiai_form"] = KiekiaiTerminaiForm()
        ctx["kabinimas_form"] = KabinimasRemaiForm()
        ctx["pakavimas_form"] = PakavimasForm()
        ctx["kainodara_form"] = KainodaraForm()
        FS = build_kainos_partijai_formset()
        ctx["kainos_partijai_formset"] = FS(prefix="kainos_partijai")

        ctx["ident_form"] = DetalesIdentifikacijaForm()
        ctx["spec_form"] = DetalesSpecifikacijaForm()
        ctx["dangos_form"] = PavirsiaiDangosForm()
        return render(request, self.template_name, ctx)

    @transaction.atomic
    def post(self, request, *args, **kwargs):
        ctx = _context_base()
        uzklausa_form = UzklausaForm(request.POST)
        ctx["uzklausa_form"] = uzklausa_form

        if not uzklausa_form.is_valid():
            messages.error(request, "Patikrinkite privalomus laukus.")
            # rodom tuščius sub-formus, kad vartotojas matytų struktūrą
            ctx.update({
                "projekto_form": UzklausosProjektoDuomenysForm(request.POST),
                "kiekiai_form": KiekiaiTerminaiForm(request.POST),
                "kabinimas_form": KabinimasRemaiForm(request.POST),
                "pakavimas_form": PakavimasForm(request.POST),
                "kainodara_form": KainodaraForm(request.POST),
                "kainos_partijai_formset": build_kainos_partijai_formset()(data=request.POST, prefix="kainos_partijai"),
                "ident_form": DetalesIdentifikacijaForm(request.POST),
                "spec_form": DetalesSpecifikacijaForm(request.POST),
                "dangos_form": PavirsiaiDangosForm(request.POST),
            })
            return render(request, self.template_name, ctx)

        # Sukuriam pačią užklausą
        uzklausa: Uzklausa = uzklausa_form.save(commit=True)
        detale = uzklausa.detale  # iš formos pasirinkimo

        # Paruošiam blokų formų rinkinį „ant konkrečių instance“
        blokai = UzklausaBlokuSet.for_instances(
            uzklausa=uzklausa, detale=detale, data=request.POST, files=request.FILES, extra_partiju=3
        )

        if not (blokai.is_valid()):
            messages.error(request, "Yra klaidų blokuose — pataisykite pažymėtus laukus.")
            # grąžinam formų rinkinį su klaidomis
            ctx.update({
                "projekto_form": blokai.projekto,
                "kiekiai_form": blokai.kiekiai,
                "kabinimas_form": blokai.kabinimas,
                "pakavimas_form": blokai.pakavimas,
                "kainodara_form": blokai.kainodara,
                "kainos_partijai_formset": blokai.kainos_partijai_fs,
                "ident_form": blokai.ident,
                "spec_form": blokai.spec,
                "dangos_form": blokai.dangos,
            })
            return render(request, self.template_name, ctx)

        # Išsaugom visas sub-formas
        blokai.save(commit=True)
        messages.success(request, self.success_message)
        return redirect(_success_url_for(uzklausa))


# ========= UPDATE =========
class UzklausaUpdateView(View):
    template_name = "detaliu_registras/ivesti_uzklausa.html"  # galima naudoti tą patį
    success_message = "Užklausa sėkmingai atnaujinta."

    def get_object(self, pk: int) -> Uzklausa:
        return get_object_or_404(Uzklausa, pk=pk)

    def get(self, request, pk: int, *args, **kwargs):
        uzklausa = self.get_object(pk)
        detale = uzklausa.detale

        ctx = _context_base()
        ctx["uzklausa_form"] = UzklausaForm(instance=uzklausa)

        # Užpildytos blokų formos
        blokai = UzklausaBlokuSet.for_instances(uzklausa, detale)
        ctx.update({
            "projekto_form": blokai.projekto,
            "kiekiai_form": blokai.kiekiai,
            "kabinimas_form": blokai.kabinimas,
            "pakavimas_form": blokai.pakavimas,
            "kainodara_form": blokai.kainodara,
            "kainos_partijai_formset": blokai.kainos_partijai_fs,
            "ident_form": blokai.ident,
            "spec_form": blokai.spec,
            "dangos_form": blokai.dangos,
            "uzklausa_obj": uzklausa,
        })
        return render(request, self.template_name, ctx)

    @transaction.atomic
    def post(self, request, pk: int, *args, **kwargs):
        uzklausa = self.get_object(pk)
        detale = uzklausa.detale

        ctx = _context_base()
        uzklausa_form = UzklausaForm(request.POST, instance=uzklausa)
        ctx["uzklausa_form"] = uzklausa_form

        if not uzklausa_form.is_valid():
            messages.error(request, "Patikrinkite privalomus laukus.")
            blokai = UzklausaBlokuSet.for_instances(uzklausa, detale, data=request.POST, files=request.FILES)
            ctx.update({
                "projekto_form": blokai.projekto,
                "kiekiai_form": blokai.kiekiai,
                "kabinimas_form": blokai.kabinimas,
                "pakavimas_form": blokai.pakavimas,
                "kainodara_form": blokai.kainodara,
                "kainos_partijai_formset": blokai.kainos_partijai_fs,
                "ident_form": blokai.ident,
                "spec_form": blokai.spec,
                "dangos_form": blokai.dangos,
                "uzklausa_obj": uzklausa,
            })
            return render(request, self.template_name, ctx)

        uzklausa_form.save(commit=True)

        # Su POST duomenimis
        blokai = UzklausaBlokuSet.for_instances(uzklausa, detale, data=request.POST, files=request.FILES)
        if not blokai.is_valid():
            messages.error(request, "Yra klaidų blokuose — pataisykite pažymėtus laukus.")
            ctx.update({
                "projekto_form": blokai.projekto,
                "kiekiai_form": blokai.kiekiai,
                "kabinimas_form": blokai.kabinimas,
                "pakavimas_form": blokai.pakavimas,
                "kainodara_form": blokai.kainodara,
                "kainos_partijai_formset": blokai.kainos_partijai_fs,
                "ident_form": blokai.ident,
                "spec_form": blokai.spec,
                "dangos_form": blokai.dangos,
                "uzklausa_obj": uzklausa,
            })
            return render(request, self.template_name, ctx)

        blokai.save(commit=True)
        messages.success(request, self.success_message)
        return redirect(_success_url_for(uzklausa))


# ========= DETAIL =========
class UzklausaDetailView(DetailView):
    model = Uzklausa
    template_name = "detaliu_registras/perziureti_uzklausa.html"
    context_object_name = "uzklausa"

    def get_queryset(self):
        qs = (Uzklausa.objects
              .select_related(
                  "klientas", "projektas", "detale",
                  "projekto_duomenys", "kiekiai_terminai",
                  "kabinimas_remai", "pakavimas", "kainodara",
              )
              .prefetch_related(
                  Prefetch("kainodara__kainos_partijoms", queryset=KainosPartijai.objects.order_by("partijos_kiekis_vnt")),
              )
              )
        # papildomai prikabiname detales „palydovus“
        qs = qs.prefetch_related(
            Prefetch("detale__identifikacija"),
            Prefetch("detale__specifikacija"),
            Prefetch("detale__pavirsiu_dangos"),
        )
        return qs


# ========= LIST (su filtru) =========
class UzklausaListView(ListView):
    model = Uzklausa
    template_name = "detaliu_registras/perziureti_uzklausas.html"  # 👈 pakeista
    context_object_name = "uzklausos"
    paginate_by = 20

    def get_queryset(self):
        qs = (Uzklausa.objects
              .select_related("klientas", "projektas", "detale")
              .order_by("-id"))
        f = UzklausaFilterForm(self.request.GET or None)
        self.filter_form = f

        if f.is_valid():
            data = f.cleaned_data
            q = data.get("q")
            if q:
                qs = qs.filter(
                    Q(detale__pavadinimas__icontains=q) |
                    Q(detale__brezinio_nr__icontains=q) |
                    Q(projektas__pavadinimas__icontains=q) |
                    Q(klientas__vardas__icontains=q)
                )
            if data.get("klientas"):
                qs = qs.filter(klientas=data["klientas"])
            if data.get("projektas"):
                qs = qs.filter(projektas=data["projektas"])
            if data.get("brezinio_nr"):
                qs = qs.filter(detale__brezinio_nr__icontains=data["brezinio_nr"])
            if data.get("metalas"):
                qs = qs.filter(detale__specifikacija__metalas__icontains=data["metalas"])
            if data.get("padengimas"):
                qs = qs.filter(
                    Q(detale__pavirsiu_dangos__ktl_ec_name__icontains=data["padengimas"]) |
                    Q(detale__pavirsiu_dangos__miltelinis_name__icontains=data["padengimas"])
                )

        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["filter_form"] = getattr(self, "filter_form", UzklausaFilterForm())
        return ctx


    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["filter_form"] = getattr(self, "filter_form", UzklausaFilterForm())
        return ctx
