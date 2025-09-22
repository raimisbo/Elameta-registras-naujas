from django.urls import path
from django.views.generic import RedirectView
from . import views

app_name = "detaliu_registras"

urlpatterns = [
# Sąrašas + filtrai + donut
    path("uzklausos/", views.UzklausaListView.as_view(), name="uzklausa_list"),

    # Kurti / redaguoti užklausą
    path("ivesti_uzklausa/", views.UzklausaCreateView.as_view(), name="ivesti_uzklausa"),
    path("ivesti_uzklausa/<int:pk>/", views.UzklausaUpdateView.as_view(), name="redaguoti_uzklausa"),

    # Peržiūra
    path("perziureti_uzklausa/<int:pk>/", views.UzklausaDetailView.as_view(), name="perziureti_uzklausa"),

    # Kainos: redagavimas (viena vieta visoms kainoms)
    path(
        "perziureti_uzklausa/<int:pk>/kainos/",
        views.KainosRedagavimasView.as_view(),
        name="redaguoti_kaina",
    ),

    # ALIAS tas pats vaizdas naujos kainos pridėjimui (kad veiktų {% url 'prideti_kaina' %})
    path(
        "perziureti_uzklausa/<int:pk>/kainos/nauja/",
        views.KainosRedagavimasView.as_view(),
        name="prideti_kaina",
    ),

    # CSV importas (jeigu naudojamas)
    path("importas/", views.ImportUzklausosCSVView.as_view(), name="import_uzklausos"),
]
