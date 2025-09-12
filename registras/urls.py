from django.contrib import admin
from django.urls import path, include, re_path
from django.views.generic import RedirectView

from detaliu_registras.views import (
    IndexView,
    UzklausaCreateView,
    UzklausaListView,
    perziureti_uzklausa,
    KainaUpdateView,
    ivesti_uzklausa_dispatch,   # <— svarbu
)

urlpatterns = [
    path('admin/', admin.site.urls),

    # App su namespace (palik)
    path(
        'detaliu_registras/',
        include(('detaliu_registras.urls', 'detaliu_registras'), namespace='detaliu_registras')
    ),

    # ---- Globalūs alias'ai SENIEMS šablonams (be namespace) ----
    # Tas pats vardas 'ivesti_uzklausa' su PASIRENKAMU parametru:
    #  - /detaliu_registras/ivesti_uzklausa/               -> kurti naują
    #  - /detaliu_registras/ivesti_uzklausa/2/             -> redaguoti kainą (uzklausa_pk=2)
    re_path(
        r'^detaliu_registras/ivesti_uzklausa(?:/(?P<uzklausa_pk>\d+))?/$',
        ivesti_uzklausa_dispatch,
        name='ivesti_uzklausa'
    ),

    path(
        'detaliu_registras/perziureti_uzklausas/<int:klientas_id>/',
        UzklausaListView.as_view(),
        name='perziureti_uzklausas'
    ),
    path(
        'detaliu_registras/perziureti_uzklausa/<int:uzklausa_id>/',
        perziureti_uzklausa,
        name='perziureti_uzklausa'
    ),
    path(
        'detaliu_registras/redaguoti_kaina/<int:uzklausa_pk>/',
        KainaUpdateView.as_view(),
        name='redaguoti_kaina'
    ),

    # Globalus 'index' alias senam {% url 'index' %}
    path(
        'detaliu_registras/_index_alias/',
        RedirectView.as_view(pattern_name='detaliu_registras:index', permanent=False),
        name='index'
    ),
]
