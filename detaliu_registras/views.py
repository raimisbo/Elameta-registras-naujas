from urllib.parse import unquote as urlunquote

from django.contrib import messages
from django.db.models import Q, Count, Value, Subquery, OuterRef
from django.db.models.functions import Coalesce
from django.forms import inlineformset_factory
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse, reverse_lazy
from django.views.generic import ListView, DetailView, CreateView, UpdateView, FormView

from .services import KainosService
from .models import Uzklausa, Kaina
from .forms import (
    UzklausaFilterForm,
    UzklausaCreateOrSelectForm,
    UzklausaEditForm,
    ImportUzklausosCSVForm,
    KainaForm, KainaRedagavimoForm
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
            kaina_nuo = form.cleaned_data.get("kaina_nuo")
            kaina_iki = form.cleaned_data.get("kaina_iki")

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

            # === Anotuojame aktualią kainą (suma, EUR) kiekvienai užklausai ===
            # Remiamės tik egzistuojančiais laukais: yra_aktuali, galioja_iki, galioja_nuo
            sub_flag = Kaina.objects.filter(
                uzklausa=OuterRef("pk"),
                yra_aktuali=True,
            ).order_by("-galioja_nuo", "-id").values("suma")[:1]

            sub_open = Kaina.objects.filter(
                uzklausa=OuterRef("pk"),
                galioja_iki__isnull=True,
            ).order_by("-galioja_nuo", "-id").values("suma")[:1]

            sub_latest = Kaina.objects.filter(
                uzklausa=OuterRef("pk"),
            ).order_by("-galioja_nuo", "-id").values("suma")[:1]

            qs = qs.annotate(
                aktuali_suma=Coalesce(
                    Subquery(sub_flag),
                    Coalesce(Subquery(sub_open), Subquery(sub_latest))
                )
            )

            # === Filtravimas pagal kainą (Decimal arba None) ===
            if kaina_nuo is not None and kaina_nuo != "":
                qs = qs.filter(aktuali_suma__gte=kaina_nuo)
            if kaina_iki is not None and kaina_iki != "":
                qs = qs.filter(aktuali_suma__lte=kaina_iki)

        return form, qs

    def get_queryset(self):
        form, qs = self.build_filters()

        # papildomas donut filtras ?seg=client:<vardas> / ?seg=others
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

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        uzklausa = self.object
        ctx["dabartine_kaina"] = Kaina.objects.filter(uzklausa=uzklausa, yra_aktuali=True).first()
        try:
            ctx["kainu_istorija"] = Kaina.objects.filter(uzklausa=uzklausa).istorija()
            if ctx["dabartine_kaina"]:
                ctx["kainu_istorija"] = ctx["kainu_istorija"].exclude(pk=ctx["dabartine_kaina"].pk)
        except Exception:
            qs = Kaina.objects.filter(uzklausa=uzklausa)
            if ctx["dabartine_kaina"]:
                qs = qs.exclude(pk=ctx["dabartine_kaina"].pk)
            ctx["kainu_istorija"] = qs
        return ctx


# === Nauja užklausa ===
class UzklausaCreateView(CreateView):
    template_name = "detaliu_registras/ivesti_uzklausa.html"
    form_class = UzklausaCreateOrSelectForm

    def form_valid(self, form):
        uzklausa = form.save()
        messages.success(self.request, "Užklausa sukurta.")
        return redirect(reverse("detaliu_registras:perziureti_uzklausa", args=[uzklausa.pk]))


# === Redagavimas ===
class UzklausaUpdateView(UpdateView):
    model = Uzklausa
    template_name = "detaliu_registras/redaguoti_uzklausa.html"
    form_class = UzklausaEditForm

    def form_valid(self, form):
        uzklausa = form.save()
        messages.success(self.request, "Užklausa atnaujinta.")
        return redirect(reverse("detaliu_registras:perziureti_uzklausa", args=[uzklausa.pk]))


# === KAINOS: redagavimas per formset'ą ===
class KainosRedagavimasView(FormView):
    template_name = "detaliu_registras/redaguoti_kaina.html"
    form_class = KainaRedagavimoForm

    def dispatch(self, request, *args, **kwargs):
        self.uzklausa = get_object_or_404(Uzklausa, pk=kwargs["pk"])
        self.detale_id = kwargs.get("detale_id")  # jei norėsi kainas detalių lygiu
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        KainosService.nustatyti_nauja_kaina(
            uzklausa_id=self.uzklausa.id,
            detale_id=self.detale_id,
            suma=form.cleaned_data["suma"],
            valiuta=form.cleaned_data["valiuta"],  # formoje visada 'EUR'
            priezastis=form.cleaned_data.get("keitimo_priezastis") or "",
            user=self.request.user,
        )
        return redirect(reverse("detaliu_registras:perziureti_uzklausa", args=[self.uzklausa.id]))

    def get_formset(self, data=None):
        FormSet = inlineformset_factory(
            parent_model=Uzklausa,
            model=Kaina,
            form=KainaForm,
            extra=0,
            can_delete=True,
        )
        return FormSet(data=data, instance=self.uzklausa)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["uzklausa"] = self.uzklausa
        ctx["formset"] = kwargs.get("formset", self.get_formset())
        return ctx

    def get(self, request, *args, **kwargs):
        formset = self.get_formset()
        return self.render_to_response(self.get_context_data(formset=formset))

    def post(self, request, *args, **kwargs):
        formset = self.get_formset(data=request.POST)
        if not formset.is_valid():
            messages.error(self.request, "Patikrinkite kainų formą.")
            return self.render_to_response(self.get_context_data(formset=formset))

        instances = formset.save(commit=False)

        # trinti pažymėtas
        for obj in formset.deleted_objects:
            obj.delete()

        # išsaugoti/atnaujinti
        for inst in instances:
            inst.uzklausa = self.uzklausa
            inst.save()

        # užtikrinti, kad liktų tik viena "aktuali"
        aktualios = Kaina.objects.aktualios().filter(uzklausa=self.uzklausa).order_by("id")
        if aktualios.count() > 1:
            palikti = aktualios.last()
            (Kaina.objects
                .filter(uzklausa=self.uzklausa, yra_aktuali=True)
                .exclude(pk=palikti.pk)
                .update(yra_aktuali=False))

        messages.success(request, "Kainos išsaugotos.")
        return redirect(reverse("detaliu_registras:perziureti_uzklausa", args=[self.uzklausa.pk]))


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
