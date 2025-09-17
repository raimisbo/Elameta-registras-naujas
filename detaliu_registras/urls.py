# detaliu_registras/urls.py
from django.urls import path
from django.views.generic import RedirectView
from . import views

app_name = "detaliu_registras"

urlpatterns = [
    # Pagrindinis app adresas -> sąrašas
    path(
        "",
        RedirectView.as_view(pattern_name="detaliu_registras:uzklausa_list", permanent=False),
        name="index",
    ),

    # Sąrašas
    path("uzklausos/", views.UzklausaListView.as_view(), name="uzklausa_list"),

    # Sukūrimas
    path("ivesti_uzklausa/", views.UzklausaCreateView.as_view(), name="ivesti_uzklausa"),

    # Redagavimas
    path("ivesti_uzklausa/<int:pk>/", views.UzklausaUpdateView.as_view(), name="redaguoti_uzklausa"),

    # Peržiūra
    path("perziureti_uzklausa/<int:pk>/", views.UzklausaDetailView.as_view(), name="perziureti_uzklausa"),
]
