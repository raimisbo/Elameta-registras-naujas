from django.urls import path
from . import views


app_name = 'detaliu_registras'

urlpatterns = [
    # Dashboard (CBV)
    path('', views.IndexView.as_view(), name='index'),

    # Requests (Uzklausos) – dabartiniai pavadinimai
    path('uzklausos/', views.UzklausaListView.as_view(), name='uzklausa_list'),
    path('uzklausos/naujas/', views.UzklausaCreateView.as_view(), name='uzklausa_create'),
    path('uzklausos/<int:pk>/', views.UzklausaDetailView.as_view(), name='uzklausa_detail'),
    path('uzklausos/<int:pk>/redaguoti/', views.UzklausaUpdateView.as_view(), name='uzklausa_update'),

    # Prices (Kainos)
    path('uzklausos/<int:uzklausa_pk>/kainos/', views.KainaListView.as_view(), name='kaina_list'),
    path('uzklausos/<int:uzklausa_pk>/kainos/redaguoti/', views.KainaUpdateView.as_view(), name='kaina_update'),

    # Client requests
    path('klientai/<int:klientas_id>/uzklausos/', views.KlientoUzklausosView.as_view(), name='kliento_uzklausos'),

    # Utilities
    path('import-csv/', views.ImportCSVView.as_view(), name='import_csv'),

    # ---- Suderinamumo alias’ai su SENAIIS ŠABLONAIS (NEKEIČIANT UI) ----
    # { % url 'ivesti_uzklausa' % }
    path('ivesti_uzklausa/', views.UzklausaCreateView.as_view(), name='ivesti_uzklausa'),
    # { % url 'perziureti_uzklausas' klientas_id=0 % }
    path('perziureti_uzklausas/<int:klientas_id>/', views.UzklausaListView.as_view(), name='perziureti_uzklausas'),
    # { % url 'perziureti_uzklausa' uzklausa_id=... % }
    path('perziureti_uzklausa/<int:uzklausa_id>/', views.perziureti_uzklausa, name='perziureti_uzklausa'),
    path('redaguoti_kaina/<int:uzklausa_pk>/', views.KainaUpdateView.as_view(), name='redaguoti_kaina'),
]
