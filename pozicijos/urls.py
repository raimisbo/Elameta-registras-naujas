from django.urls import path
from . import views
from . import proposal_views
from . import kainos_views   # <-- naujas import

app_name = "pozicijos"

urlpatterns = [
    path("", views.pozicijos_list, name="list"),
    path("tbody/", views.pozicijos_tbody, name="tbody"),
    path("stats/", views.pozicijos_stats, name="stats"),
    path("new/", views.pozicija_create, name="create"),
    path("<int:pk>/", views.pozicija_detail, name="detail"),
    path("<int:pk>/edit/", views.pozicija_edit, name="edit"),

    # pasiūlymui
    path("<int:pk>/proposal/", proposal_views.proposal_prepare, name="proposal_prepare"),
    path("<int:pk>/pdf/", proposal_views.proposal_pdf, name="pdf"),

    # kainoms
    path("<int:pk>/kainos/", kainos_views.kainos_list, name="kainos_list"),
    path("<int:pk>/kainos/new/", kainos_views.kaina_add, name="kaina_add"),
    path("<int:pk>/kainos/<int:kaina_id>/edit/", kainos_views.kaina_edit, name="kaina_edit"),
    path("<int:pk>/kainos/<int:kaina_id>/delete/", kainos_views.kaina_delete, name="kaina_delete"),
]
