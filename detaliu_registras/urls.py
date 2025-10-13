# detaliu_registras/urls.py
from django.urls import path
from . import views

app_name = "detaliu_registras"

urlpatterns = [
    # ALIAS: /detaliu_registras/ -> senasis sąrašas (kad nebekristų 404)
    path("", views.UzklausaListView.as_view(), name="uzklausa_list_alias"),

    # Senasis sąrašas
    path("uzklausos/", views.UzklausaListView.as_view(), name="uzklausa_list"),

    # Nauja užklausa
    path("ivesti_uzklausa/", views.UzklausaCreateView.as_view(), name="ivesti_uzklausa"),

    # Peržiūra (palieku abu variantus dėl suderinamumo)
    path("perziureti_uzklausa/<int:pk>/", views.UzklausaDetailView.as_view(), name="perziureti_uzklausa"),
    path("perziureti_uzklausa/<int:uzklausa_id>/", views.UzklausaDetailView.as_view(), name="perziureti_uzklausa"),

    # Redagavimas (tas pats principas)
    path("ivesti_uzklausa/<int:pk>/", views.UzklausaUpdateView.as_view(), name="redaguoti_uzklausa"),
    path("ivesti_uzklausa/<int:uzklausa_id>/", views.UzklausaUpdateView.as_view(), name="redaguoti_uzklausa"),

    # Kainos
    path("perziureti_uzklausa/<int:pk>/kainos/", views.KainosRedagavimasView.as_view(), name="redaguoti_kaina"),
    path("perziureti_uzklausa/<int:uzklausa_id>/kainos/", views.KainosRedagavimasView.as_view(), name="redaguoti_kaina"),

    path("perziureti_uzklausa/<int:pk>/kainos/nauja/", views.KainosRedagavimasView.as_view(), name="prideti_kaina"),
    path("perziureti_uzklausa/<int:uzklausa_id>/kainos/nauja/", views.KainosRedagavimasView.as_view(), name="prideti_kaina"),

    # CSV importas
    path("importas/", views.ImportUzklausosCSVView.as_view(), name="import_uzklausos"),
]
