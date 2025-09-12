from django.shortcuts import render, redirect, get_object_or_404
from django.views.generic import ListView, DetailView, CreateView, UpdateView, TemplateView
from django.db.models import Q, Count
from django.contrib import messages
from django.forms import formset_factory, modelformset_factory,inlineformset_factory
from django.template import TemplateDoesNotExist
import json
import logging

from .models import Klientas, Detale, Uzklausa, Projektas, Kaina
from .forms import (
    ImportCSVForm, UzklausaCreationForm, KainaForm,
    UzklausaFilterForm, DetaleForm, ProjektasForm,KlientasForm
)
from .services import UzklausaService
from .utils import import_csv

logger = logging.getLogger(__name__)


# --------------------------
# Pagalbinės funkcijos
# --------------------------

def convert_network_path_to_url(network_path):
    """
    Konvertuoja tinklo kelią (\\server\dir\file) į HTTP-lik kelią (server/dir/file).
    Gražina None, jei įėjimas None arba tuščias.
    """
    if not network_path:
        return None
    s = str(network_path)
    if s.startswith("http://") or s.startswith("https://"):
        return s
    return s.strip("\\").replace("\\", "/")


# --------------------------
# Pagrindiniai vaizdai
# --------------------------

class IndexView(TemplateView):
    """
    Pradinis dashboard puslapis su klientų statistika.
    Išlaikome seną išvaizdą – fallback į 'index.html', jei app prefiksuoto nėra.
    """
    template_name = "detaliu_registras/index.html"

    def get_template_names(self):
        return ["detaliu_registras/index.html", "index.html"]

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        klientu_duomenys = (
            Uzklausa.objects.values('klientas__vardas', 'klientas__id')
            .annotate(kiekis=Count('id'))
        )
        context.update({
            "uzklausos": Uzklausa.objects.select_related("klientas", "projektas", "detale")[:10],
            "klientu_duomenys_json": json.dumps(list(klientu_duomenys)),
        })
        return context


class UzklausaListView(ListView):
    """
    Užklausų sąrašas su filtru ir suderinamumu 'klientas_id' URL paramui (senas maršrutas).
    """
    model = Uzklausa
    template_name = "detaliu_registras/uzklausa_list.html"
    context_object_name = "uzklausos"
    paginate_by = 20

    def get_template_names(self):
        # 1) naujas pavadinimas; 2-3) seni pavadinimai (su ir be app prefikso)
        return [
            "detaliu_registras/uzklausa_list.html",
            "detaliu_registras/perziureti_uzklausas.html",
            "perziureti_uzklausas.html",
        ]

    def get_queryset(self):
        queryset = Uzklausa.objects.select_related('klientas', 'projektas', 'detale').all()

        # Suderinamumas su senu maršrutu /perziureti_uzklausas/<klientas_id>/
        klientas_id = self.kwargs.get('klientas_id')
        if klientas_id is not None:
            try:
                kid = int(klientas_id)
                if kid > 0:
                    queryset = queryset.filter(klientas_id=kid)
            except (TypeError, ValueError):
                pass

        query = self.request.GET.get('q', '')
        if query:
            queryset = queryset.filter(
                Q(klientas__vardas__icontains=query) |
                Q(projektas__pavadinimas__icontains=query) |
                Q(detale__pavadinimas__icontains=query) |
                Q(detale__brezinio_nr__icontains=query)
            )
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        try:
            context['filter_form'] = UzklausaFilterForm(self.request.GET)
        except Exception:
            context['filter_form'] = None
        return context


class UzklausaDetailView(DetailView):
    """
    Vienos užklausos detalės (naujas kelias).
    Šablono fallback’ai leidžia naudoti senuosius 'perziureti_uzklausa.html' pavadinimus.
    """
    model = Uzklausa
    template_name = "detaliu_registras/uzklausa_detail.html"
    context_object_name = "uzklausa"

    def get_template_names(self):
        return [
            "detaliu_registras/uzklausa_detail.html",
            "detaliu_registras/perziureti_uzklausa.html",
            "perziureti_uzklausa.html",
        ]

    def get_queryset(self):
        return Uzklausa.objects.select_related('klientas', 'projektas', 'detale') \
                               .prefetch_related('detale__kainos')


class UzklausaCreateView(CreateView):
    """
    Naudojam kompozitinę formą UzklausaCreationForm,
    BET į kontekstą taip pat paduodam senus šablono kintamuosius:
    uzklausa_form, klientas_form, projektas_form, detale_form, kaina_formset.
    """
    form_class = UzklausaCreationForm
    template_name = "detaliu_registras/uzklausa_create.html"

    def get_template_names(self):
        # paliakau senus pavadinimus
        return [
            "detaliu_registras/uzklausa_create.html",
            "detaliu_registras/ivesti_uzklausa.html",
            "uzklausa_create.html",
            "ivesti_uzklausa.html",
        ]

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs.pop('instance', None)  # CreateView prideda 'instance' -> pašalinam (čia ne ModelForm)
        return kwargs

    def _kaina_formset_class(self):
        return modelformset_factory(
            Kaina,
            form=KainaForm,
            extra=1,
            can_delete=True,
        )

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)

        # Pagrindinė kompozitinė forma (naudojama servisui)
        form = ctx.get('form') or self.get_form()
        ctx['form'] = form
        ctx['uzklausa_form'] = form  # senasis šablonas tikisi šito vardo

        # Senasis šablonas dažnai rodo atskiras "subformas" – paduodam tuščias (kad būtų input’ai)
        ctx.setdefault('klientas_form', KlientasForm())
        ctx.setdefault('projektas_form', ProjektasForm())
        ctx.setdefault('detale_form', DetaleForm())

        # Kainų formset’as (privaloma: management form turi būti šablone)
        KainaFS = self._kaina_formset_class()
        # kuriant naują – dar nėra kainų, todėl queryset=none()
        ctx['kaina_formset'] = kwargs.get('kaina_formset') or KainaFS(queryset=Kaina.objects.none())

        return ctx

    def post(self, request, *args, **kwargs):
        # Surenkam visas dalis
        form = self.get_form()
        KainaFS = modelformset_factory(Kaina, form=KainaForm, extra=1, can_delete=True)
        kaina_formset = KainaFS(request.POST, queryset=Kaina.objects.none())

        # (Pas tave šablonas gali POST’inti ir atskirų subformų laukus – jų nenaudojame validacijai,
        #  nes logiką atlieka servisas, bet jos reikalingos, kad būtų input’ai UI.)
        klientas_form = KlientasForm(request.POST or None)
        projektas_form = ProjektasForm(request.POST or None)
        detale_form = DetaleForm(request.POST or None)

        if form.is_valid() and kaina_formset.is_valid():
            try:
                # Sukuriam UZKLAUSA, PROJEKTĄ, DETALĘ per serviso sluoksnį
                uzklausa = UzklausaService.create_full_request(form.cleaned_data)

                # Pririšam kainas prie ką tik sukurtos detalės
                instances = kaina_formset.save(commit=False)
                for obj in instances:
                    obj.detale = uzklausa.detale
                    obj.save()
                for obj in kaina_formset.deleted_objects:
                    # teoriškai nieko čia nebus kuriant naują, bet paliekam pilnumui
                    obj.delete()

                messages.success(request, "Užklausa sukurta, kainos išsaugotos")
                return redirect("detaliu_registras:uzklausa_detail", pk=uzklausa.pk)

            except Exception as e:
                logger.error(f"Klaida kuriant užklausą: {e}")
                messages.error(request, "Klaida kuriant užklausą")

        # Jei klaidos – grąžinam tą patį puslapį su visomis formomis / formset’u
        ctx = self.get_context_data(
            form=form,
            klientas_form=klientas_form,
            projektas_form=projektas_form,
            detale_form=detale_form,
            kaina_formset=kaina_formset,
        )
        return self.render_to_response(ctx)


class UzklausaUpdateView(TemplateView):
    """
    Suderinamumo „tiltas“ – jei senas maršrutas kviečia redagavimą, grąžinam į detalių peržiūrą.
    """
    def get(self, request, pk):
        return redirect('detaliu_registras:uzklausa_detail', pk=pk)


class KainaListView(TemplateView):
    """
    Suderinamumo „tiltas“ – nukreipiam į tą pačią redagavimo formą.
    """
    def get(self, request, uzklausa_pk):
        return redirect('detaliu_registras:kaina_update', uzklausa_pk=uzklausa_pk)


class KainaUpdateView(UpdateView):
    """
    Pilnai redaguojamos kainos per InlineFormSet (Detale -> Kaina).
    """
    def get_template_names(self):
        return [
            "detaliu_registras/kaina_update.html",
            "detaliu_registras/redaguoti_kaina.html",
            "kaina_update.html",
            "redaguoti_kaina.html",
        ]

    def _render_with_fallback(self, request, context):
        last_exc = None
        for tpl in self.get_template_names():
            try:
                return render(request, tpl, context)
            except TemplateDoesNotExist as e:
                last_exc = e
                continue
        raise TemplateDoesNotExist(", ".join(self.get_template_names())) from last_exc

    def _get_formset_class(self):
        # Inline formset automatiškai nustato kaina.detale = instance
        return inlineformset_factory(
            Detale,
            Kaina,
            form=KainaForm,
            extra=1,
            can_delete=True,
        )

    def get(self, request, uzklausa_pk):
        uzklausa = get_object_or_404(Uzklausa.objects.select_related("detale"), pk=uzklausa_pk)
        FormSet = self._get_formset_class()
        formset = FormSet(instance=uzklausa.detale)
        return self._render_with_fallback(request, {"formset": formset, "uzklausa": uzklausa})

    def post(self, request, uzklausa_pk):
        uzklausa = get_object_or_404(Uzklausa.objects.select_related("detale"), pk=uzklausa_pk)
        FormSet = self._get_formset_class()
        formset = FormSet(request.POST, instance=uzklausa.detale)

        if formset.is_valid():
            formset.save()  # išsaugo naujas/redaguotas/trinamas kainas
            messages.success(request, "Kainos atnaujintos")
            return redirect("perziureti_uzklausa", uzklausa_id=uzklausa.pk)

        return self._render_with_fallback(request, {"formset": formset, "uzklausa": uzklausa})


class ImportCSVView(TemplateView):
    """
    CSV importas – su paprastu pranešimų mechanizmu.
    """
    template_name = "detaliu_registras/import_csv.html"

    def get_template_names(self):
        return ["detaliu_registras/import_csv.html", "import_csv.html"]

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['form'] = ImportCSVForm()
        return context

    def post(self, request):
        form = ImportCSVForm(request.POST, request.FILES)
        if form.is_valid():
            try:
                # palaikome tiek 'file', tiek 'csv_file' laukų pavadinimus
                uploaded = form.cleaned_data.get('file') or form.cleaned_data.get('csv_file') \
                           or request.FILES.get('file') or request.FILES.get('csv_file')
                if not uploaded:
                    raise ValueError("Nerastas CSV failas (laukas 'file' arba 'csv_file').")
                import_csv(uploaded)
                messages.success(request, "CSV failas sėkmingai importuotas")
                return redirect("admin:index")
            except Exception as e:
                logger.error(f"CSV importo klaida: {e}")
                messages.error(request, "Klaida importuojant CSV failą")
        return render(request, self.template_name, {'form': form})


class KlientoUzklausosView(ListView):
    """
    Konkretaus kliento užklausos (senas šablonas išlaikomas per fallback).
    """
    model = Uzklausa
    template_name = "detaliu_registras/kliento_uzklausos.html"
    context_object_name = "uzklausos"

    def get_template_names(self):
        return ["detaliu_registras/kliento_uzklausos.html", "kliento_uzklausos.html"]

    def get_queryset(self):
        klientas_id = self.kwargs['klientas_id']
        return Uzklausa.objects.filter(
            klientas_id=klientas_id
        ).select_related('projektas', 'detale')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        klientas_id = self.kwargs['klientas_id']
        context['klientas'] = get_object_or_404(Klientas, pk=klientas_id)
        return context


# --------------------------
# Suderinamumo vaizdai
# --------------------------

def perziureti_uzklausa(request, uzklausa_id):
    """
    Senas maršrutas 'perziureti_uzklausa/<id>/' – šablonas 'perziureti_uzklausa.html' palaikomas.
    """
    uzklausa = get_object_or_404(
        Uzklausa.objects.select_related("detale", "klientas", "projektas"),
        pk=uzklausa_id
    )
    brezinio_url = convert_network_path_to_url(getattr(uzklausa.detale, "nuoroda_brezinio", None))
    ctx = {"uzklausa": uzklausa, "brezinio_url": brezinio_url}
    return render(request, "detaliu_registras/perziureti_uzklausa.html", ctx)


def ivesti_uzklausa_dispatch(request, uzklausa_pk=None):
    """
    Tas pats URL vardas 'ivesti_uzklausa' dirba dviem režimais, kad senų šablonų nekeisti:
      - be argumento -> naujos užklausos kūrimas (UzklausaCreateView)
      - su <uzklausa_pk> -> kainų redagavimas (KainaUpdateView)
    """
    if uzklausa_pk is not None:
        return KainaUpdateView.as_view()(request, uzklausa_pk=uzklausa_pk)
    return UzklausaCreateView.as_view()(request)
