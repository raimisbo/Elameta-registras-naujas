# pozicijos/urls.py
from django.urls import path
from . import views
from . import proposal_views
from . import kainos_views

app_name = "pozicijos"

urlpatterns = [
    # sąrašas
    path("", views.pozicijos_list, name="list"),
    path("tbody/", views.pozicijos_tbody, name="tbody"),
    path("stats/", views.pozicijos_stats, name="stats"),

    # kurti / redaguoti
    path("nauja/", views.pozicija_create, name="create"),
    path("<int:pk>/redaguoti/", views.pozicija_edit, name="edit"),

    # detalė
    path("<int:pk>/", views.pozicija_detail, name="detail"),

    # brėžiniai
    path("<int:pk>/breziniai/upload/", views.brezinys_upload, name="brezinys_upload"),
    path("<int:pk>/breziniai/<int:bid>/delete/", views.brezinys_delete, name="brezinys_delete"),

    # pasiūlymai
    path("<int:pk>/proposal/", proposal_views.proposal_prepare, name="proposal_prepare"),
    path("<int:pk>/pdf/", proposal_views.proposal_pdf, name="pdf"),

    # KAINOS (nauja)
    path("<int:pk>/kainos/", kainos_views.kainos_list, name="kainos_list"),
    path("<int:pk>/kainos/nauja/", kainos_views.kaina_create, name="kaina_create"),
    path("kainos/<int:id>/redaguoti/", kainos_views.kaina_update, name="kaina_update"),
    path("kainos/<int:id>/aktuali/", kainos_views.kaina_set_aktuali, name="kaina_set_aktuali"),
    path("kainos/<int:id>/salinti/", kainos_views.kaina_delete, name="kaina_delete"),
]
