# pozicijos/urls.py
from django.urls import path
from . import views
from . import proposal_views  # pasiūlymo parengimas / pdf

app_name = "pozicijos"

urlpatterns = [
    # sąrašas + ajax dalys
    path("", views.pozicijos_list, name="list"),
    path("tbody/", views.pozicijos_tbody, name="tbody"),
    path("stats/", views.pozicijos_stats, name="stats"),  # grafiko/donut endpoint

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
]
