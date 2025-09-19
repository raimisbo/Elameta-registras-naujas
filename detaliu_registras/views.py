from urllib.parse import unquote as urlunquote

from django.contrib import messages
from django.db.models import Q, Count, Value
from django.db.models.functions import Coalesce
from django.shortcuts import redirect
from django.urls import reverse, reverse_lazy
from django.views.generic import ListView, DetailView, CreateView, UpdateView, FormView

from .models import Uzklausa
from .forms import (
    UzklausaFilterForm,
    UzklausaCreateOrSelectForm,
    UzklausaEditForm,
    ImportUzklausosCSVForm,
)

# CSV importo helperis (nebūtinas)
try:
    from .importers import import_uzklausos_csv
except Exception:
    import_uzklausos_csv = None


# === Sąrašas su filtrais ir donut ===
class UzklausaListView(ListView):
    model = Uzklausa
    template_name = "detaliu_registras/perziureti_uzklausas.html"
    context_object_name = "uzklausos"
    paginate_by = 25

    def get_base_queryset(self):
        return (
            Uzklausa.objects
            .select_related(
                "klientas", "projektas", "detale",
                "detale__specifikacija", "detale__pavirsiu_dangos"
            )
            .order_by("-id")
        )

    def build_filters(self):
        qs = self.get_base_queryset()
        form = UzklausaFilterForm(self.request.GET or None)

        if form.is_valid():
            q = form.cleaned_data.get("q")
            klientas = form.cleaned_data.get("klientas")
            projektas = form.cleaned_data.get("projektas")
            detale = form.cleaned_data.get("detale")
            brezinio_nr = form.cleaned_data.get("brezinio_nr")
            metalas = form.cleaned_data.get("metalas")
            padengimas = form.cleaned_data.get("padengimas")

            if q:
                qs = qs.filter(
                    Q(detale__pavadinimas__icontains=q) |
                    Q(detale__brezinio_nr__icontains=q) |
                    Q(klientas__vardas__icontains=q) |
                    Q(projektas__pavadinimas__icontains=q)
                )
            if klientas:
                qs = qs.filter(klientas=klientas)
            if projektas:
                qs = qs.filter(projektas=projektas)
            if detale:
                qs = qs.filter(detale=detale)
            if brezinio_nr:
                qs = qs.filter(detale__brezinio_nr__icontains=brezinio_nr)
            if metalas:
                qs = qs.filter(detale__specifikacija__metalas__icontains=metalas)
            if padengimas:
                qs = qs.filter(
                    Q(detale__pavirsiu_dangos__ktl_ec_name__icontains=padengimas) |
                    Q(detale__pavirsiu_dangos__miltelinis_name__icontains=padengimas)
                )

        return form, qs

    def get_queryset(self):
        form, qs = self.build_filters()

        # Papildomas donut filtras ?seg=client:<vardas> / ?seg=others
        seg = self.request.GET.get("seg")
        if seg:
            top_names = list(
                qs.values_list(Coalesce("klientas__vardas", Value("Be kliento")), flat=True)
                  .annotate(c=Count("id"))
                  .order_by("-c")[:5]
            )
            if seg == "others":
                qs = qs.exclude(klientas__vardas__in=top_names)
            elif seg.startswith("client:"):
                name = urlunquote(seg.split("client:", 1)[1])
                if name == "Be kliento":
                    qs = qs.filter(klientas__isnull=True)
                else:
                    qs = qs.filter(klientas__vardas=name)

        self._filter_form = form
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["filter_form"] = getattr(self, "_filter_form", UzklausaFilterForm())

        qs_all = self.get_queryset().select_related("klientas")
        total = qs_all.count()
        top_rows = (
            qs_all.values(label=Coalesce("klientas__vardas", Value("Be kliento")))
                  .annotate(value=Count("id"))
                  .order_by("-value")[:5]
        )
        segments = [{"label": r["label"], "value": r["value"], "slug": f"client:{r['label']}"} for r in top_rows]
        sum_top = sum(r["value"] for r in top_rows)
        others = max(0, total - sum_top)
        if others > 0:
            segments.append({"label": "Kiti", "value": others, "slug": "others"})

        ctx["chart_total"] = total
        ctx["chart_segments"] = segments
        ctx["active_seg"] = self.request.GET.get("seg", "")
        return ctx


# === Peržiūra ===
class UzklausaDetailView(DetailView):
    model = Uzklausa
    template_name = "detaliu_registras/perziureti_uzklausa.html"
    context_object_name = "uzklausa"


# === Nauja užklausa: po sukūrimo – į peržiūrą ===
class UzklausaCreateView(CreateView):
    template_name = "detaliu_registras/ivesti_uzklausa.html"
    form_class = UzklausaCreateOrSelectForm

    def form_valid(self, form):
        uzklausa = form.save()
        messages.success(self.request, "Užklausa sukurta.")
        return redirect(reverse("detaliu_registras:perziureti_uzklausa", args=[uzklausa.pk]))


# === Redagavimas: po išsaugojimo – į peržiūrą ===
class UzklausaUpdateView(UpdateView):
    model = Uzklausa
    template_name = "detaliu_registras/redaguoti_uzklausa.html"
    form_class = UzklausaEditForm
    # success_url = reverse_lazy("detaliu_registras:uzklausa_list")  # nebereikia

    def form_valid(self, form):
        uzklausa = form.save()
        messages.success(self.request, "Užklausa atnaujinta.")
        return redirect(reverse("detaliu_registras:perziureti_uzklausa", args=[uzklausa.pk]))


# === CSV importas (stub) ===
class ImportUzklausosCSVView(FormView):
    template_name = "detaliu_registras/import_uzklausos.html"
    form_class = ImportUzklausosCSVForm
    success_url = reverse_lazy("detaliu_registras:import_uzklausos")

    def form_valid(self, form):
        if import_uzklausos_csv is None:
            messages.error(self.request, "Importavimo modulis nerastas: detaliu_registras/importers.py")
            return super().form_valid(form)

        stats = import_uzklausos_csv(self.request.FILES["file"])
        if stats.get("errors"):
            for row, err in stats["errors"][:10]:
                messages.error(self.request, f"Eilutė {row}: {err}")
        messages.success(self.request, f"Sukurta: {stats.get('created',0)}, atnaujinta: {stats.get('updated',0)}, praleista: {stats.get('skipped',0)}")
        return super().form_valid(form)
