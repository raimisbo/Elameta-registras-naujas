from django.urls import path
from django.views.generic import RedirectView
from . import views

app_name = "detaliu_registras"

urlpatterns = [
    path("", RedirectView.as_view(pattern_name="detaliu_registras:uzklausa_list", permanent=False), name="index"),
    path("uzklausos/", views.UzklausaListView.as_view(), name="uzklausa_list"),
    path("ivesti_uzklausa/", views.UzklausaCreateView.as_view(), name="ivesti_uzklausa"),
    path("ivesti_uzklausa/<int:pk>/", views.UzklausaUpdateView.as_view(), name="redaguoti_uzklausa"),
    path("perziureti_uzklausa/<int:pk>/", views.UzklausaDetailView.as_view(), name="perziureti_uzklausa"),
    path("importas/", views.ImportUzklausosCSVView.as_view(), name="import_uzklausos"),
]
