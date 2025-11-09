# pozicijos/urls.py
from django.urls import path
from . import views

app_name = "pozicijos"

urlpatterns = [
    path("", views.pozicijos_list, name="list"),
    path("tbody/", views.pozicijos_tbody, name="tbody"),
    path("stats/", views.pozicijos_stats, name="stats"),
    path("nauja/", views.pozicija_create, name="create"),
    path("<int:pk>/", views.pozicija_detail, name="detail"),
    path("<int:pk>/redaguoti/", views.pozicija_edit, name="edit"),
    path("<int:pk>/kainos/", views.pozicijos_kainos_redaguoti, name="kainos"),
]
