from django.shortcuts import render, redirect, get_object_or_404
from django.db import models
from .models import Klientas, Detale, Uzklausa, Projektas, Kaina
from django.db.models import Count, Q
from .forms import ImportCSVForm, IvestiUzklausaForm, KainaForm, UzklausaFilterForm
from django.forms import formset_factory
from .utils import import_csv
from django.views.decorators.csrf import csrf_protect
import json
import logging
import urllib.parse

logger = logging.getLogger(__name__)

# Create your views here.

def index(request):
    uzklausos = Uzklausa.objects.all()
    form = UzklausaFilterForm()
    klientu_duomenys = Uzklausa.objects.values('klientas__vardas', 'klientas__id').annotate(
        kiekis=models.Count('id')  # Skaičiuojame kiekvieno kliento įrašų kiekį
    )
 
    klientu_duomenys_json = json.dumps(list(klientu_duomenys))
    
    context = {'uzklausos': uzklausos, 
       'klientu_duomenys_json': klientu_duomenys_json,
    }
    return render(request, 'index.html', context)


def ivesti_uzklausa(request):
    # Čia įdėkite kodą, kuris sugeneruos užklausos įvedimo formą
    return render(request, 'detaliu_registras/ivesti_uzklausa.html')

def perziureti_uzklausas(request, klientas_id):
    query = request.GET.get('q', '')

    uzklausos = Uzklausa.objects.all()

    if query:
        uzklausos = uzklausos.filter(
            Q(klientas__vardas__icontains=query) |
            Q(projektas__pavadinimas__icontains=query) |
            Q(detale__pavadinimas__icontains=query) |
            Q(detale__brezinio_nr__icontains=query)
        )
    
    context = {
        'uzklausos': uzklausos,
        'request': request
    }
    return render(request, 'detaliu_registras/perziureti_uzklausas.html', context)

def import_csv_view(request):
    if request.method == 'POST':
        form = ImportCSVForm(request.POST, request.FILES)
        if form.is_valid():
            import_csv(form.cleaned_data['csv_file'])
            return redirect('admin:index')  # Arba kitą peradresavimo puslapį
    else:
        form = ImportCSVForm()
    return render(request, 'detaliu_registras/import_csv.html', {'form': form})


def convert_network_path_to_url(network_path):
    # Pakeisti atbulus brūkšnius į tiesius brūkšnius
    http_path = network_path.strip('\\').replace('\\', '/')
    
    # Pridėti protokolą (HTTP) ir užkoduoti specialius simbolius
    
    http_path = http_path.strip('"')
    
    encoded_url = urllib.parse.quote(http_path, safe=':/')
    
    return encoded_url

def perziureti_uzklausa(request, uzklausa_id, brėžinio_url=None):
    
    uzklausa = get_object_or_404(Uzklausa, id=uzklausa_id)
    brėžinio_url = convert_network_path_to_url(uzklausa.detale.nuoroda_brezinio)
    logger.info(f"Received URL params: uzklausa_id={uzklausa_id}, brėžinio_url={brėžinio_url}")
    if brėžinio_url:
        brėžinio_url = urllib.parse.unquote(brėžinio_url)
    context = {
        'uzklausa': uzklausa,
        "brėžinio_url": brėžinio_url
    }
    return render(request, 'detaliu_registras/perziureti_uzklausa.html', context)

def ivesti_uzklausa(request, uzklausa_id=None):
    KainaFormSet = formset_factory(KainaForm, extra=1, can_delete=True)
    
    if uzklausa_id:
        uzklausa = get_object_or_404(Uzklausa, id=uzklausa_id)
        detale = uzklausa.detale
        if request.method == 'POST':
            uzklausa_form = IvestiUzklausaForm(request.POST, instance=uzklausa)
            kaina_formset = KainaFormSet(request.POST)
        else:
            uzklausa_form = IvestiUzklausaForm(instance=uzklausa)
            kaina_initial = [{'busena': k.busena, 'suma': k.suma, 'kiekis_nuo': k.kiekis_nuo, 'kiekis_iki': k.kiekis_iki, 'fiksuotas_kiekis': k.fiksuotas_kiekis, 'kainos_matas': k.kainos_matas} for k in Kaina.objects.filter(detalė=detale)]
            kaina_formset = KainaFormSet(initial=kaina_initial)
    else:
        if request.method == 'POST':
            uzklausa_form = IvestiUzklausaForm(request.POST)
            kaina_formset = KainaFormSet(request.POST)
        else:
            uzklausa_form = IvestiUzklausaForm()
            kaina_formset = KainaFormSet()
    
    if request.method == 'POST':
        if uzklausa_form.is_valid() and kaina_formset.is_valid():
            if uzklausa_id:
                uzklausa.save()
                detale = uzklausa.detale
            else:
                # Išsaugome projekto duomenis
                projektas = Projektas.objects.create(
                    klientas=uzklausa_form.cleaned_data['klientas'],
                    pavadinimas=uzklausa_form.cleaned_data['projekto_pavadinimas'],
                    uzklausos_data=uzklausa_form.cleaned_data['uzklausos_data'],
                    pasiulymo_data=uzklausa_form.cleaned_data['pasiulymo_data']
                )
			
                # Išsaugome detalės duomenis
                detale = Detale.objects.create(
                    projektas=projektas,
                    pavadinimas=uzklausa_form.cleaned_data['detales_pavadinimas'],
                    brezinio_nr=uzklausa_form.cleaned_data['brezinio_nr'],
                    plotas=uzklausa_form.cleaned_data['plotas'],
                    svoris=uzklausa_form.cleaned_data['svoris'],
                    kiekis_metinis=uzklausa_form.cleaned_data['kiekis_metinis'],
                    kiekis_menesis=uzklausa_form.cleaned_data.get('kiekis_menesis'),
                    kiekis_partijai=uzklausa_form.cleaned_data.get('kiekis_partijai'),
                    ppap_dokumentai=uzklausa_form.cleaned_data.get('ppap_dokumentai'),
                    standartas=uzklausa_form.cleaned_data.get('standartas'),
                    kabinimo_tipas=uzklausa_form.cleaned_data.get('kabinimo_tipas'),
                    kabinimas_xyz=uzklausa_form.cleaned_data.get('kabinimas_xyz'),
                    kiekis_reme=uzklausa_form.cleaned_data['kiekis_reme'],
                    faktinis_kiekis_reme=uzklausa_form.cleaned_data.get('faktinis_kiekis_reme', 0),
                    pakavimas=uzklausa_form.cleaned_data.get('pakavimas'),
                    nuoroda_brezinio=uzklausa_form.cleaned_data.get('nuoroda_brezinio'),
                    nuoroda_pasiulymo=uzklausa_form.cleaned_data['nuoroda_pasiulymo'],
                    pastabos=uzklausa_form.cleaned_data.get('pastabos')
                )
                detale.danga.set(uzklausa_form.cleaned_data['danga'])
                
                # Išsaugome užklausą
                uzklausa = Uzklausa.objects.create(
                    klientas=uzklausa_form.cleaned_data['klientas'],
                    projektas=projektas,
                    detale=detale
                )
            
            # Išsaugome visas kainas
            for form in kaina_formset:
                if form.cleaned_data:
                    kaina = form.save(commit=False)
                    kaina.detalė = detale
                    kaina.save()
            
            return redirect('index')
    
    context = {
        'uzklausa_form': uzklausa_form,
        'kaina_formset': kaina_formset,
    }
    return render(request, 'detaliu_registras/ivesti_uzklausa.html', context)

def redaguoti_kaina(request, uzklausa_id):
    KainaFormSet = formset_factory(KainaForm, extra=1, can_delete=True)

    # Gauti užklausą pagal ID
    uzklausa = get_object_or_404(Uzklausa, id=uzklausa_id)
    detale = uzklausa.detale

													   
    if request.method == 'POST':
        kaina_formset = KainaFormSet(request.POST)

        if kaina_formset.is_valid():
            # Gauti esamas kainas pagal detalę
            existing_kainos = Kaina.objects.filter(detalė=detale)

            # Pridėti atnaujintus ir naujus kainos objektus
            new_kainos = []
            for form in kaina_formset:
                if form.cleaned_data:
                    kaina = form.save(commit=False)
                    kaina.detalė = detale
                    # Patikrinti ar kainos ID yra ir atnaujinti arba pridėti
                    if kaina.id:
                        existing_kaina = existing_kainos.filter(id=kaina.id).first()
                        if existing_kaina:
                            # Atnaujinti esamą kainą
                            existing_kaina.busena = kaina.busena
                            existing_kaina.suma = kaina.suma
                            existing_kaina.kiekis_nuo = kaina.kiekis_nuo
                            existing_kaina.kiekis_iki = kaina.kiekis_iki
                            existing_kaina.fiksuotas_kiekis = kaina.fiksuotas_kiekis
                            existing_kaina.kainos_matas = kaina.kainos_matas
                            existing_kaina.save()
                        else:
                            # Pridėti naują kainą
                            kaina.save()
                    else:
                        # Pridėti naują kainą
                        kaina.save()
                    new_kainos.append(kaina)
            
            # Pašalinti senas kainas, jei jų nebėra formose
            for existing_kaina in existing_kainos:
                if existing_kaina not in new_kainos:
                    existing_kaina.delete()

            # Nukreipti į „Peržiūrėti užklausą“ puslapį
            return redirect('perziureti_uzklausa', uzklausa_id=uzklausa_id)
    else:
        # Užpildome formos pradines reikšmes pagal esamas kainas
        kaina_initial = [{'id': k.id, 'busena': k.busena, 'suma': k.suma, 'kiekis_nuo': k.kiekis_nuo, 'kiekis_iki': k.kiekis_iki, 'fiksuotas_kiekis': k.fiksuotas_kiekis, 'kainos_matas': k.kainos_matas} for k in Kaina.objects.filter(detalė=detale)]
        kaina_formset = KainaFormSet(initial=kaina_initial)

    context = {
        'kaina_formset': kaina_formset,
        'klientas': uzklausa.klientas.vardas,
        'projekto_pavadinimas': uzklausa.projektas.pavadinimas,
        'detales_pavadinimas': detale.pavadinimas,
        'brezinių_nr': detale.brezinio_nr,
        'uzklausa': uzklausa,  # Pridėti šią eilutę, kad būtų prieinamas užklausos ID šablone
    }
    return render(request, 'detaliu_registras/redaguoti_kaina.html', context)
