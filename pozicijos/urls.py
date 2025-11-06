# pozicijos/urls.py
from django.urls import path
from . import views

app_name = "pozicijos"

urlpatterns = [
    path("", views.PozicijuSarasasView.as_view(), name="list"),
    path("tbody/", views.PozicijuTbodyPartialView.as_view(), name="tbody"),
    path("stats/", views.PozicijuStatsView.as_view(), name="stats"),
    path("new/", views.PozicijaCreateView.as_view(), name="create"),
    path("<int:pk>/", views.PozicijaDetailView.as_view(), name="detail"),
    path("<int:pk>/edit/", views.PozicijaUpdateView.as_view(), name="edit"),
    path("detale/<slug:slug>/", views.PozicijosKorteleView.as_view(), name="detail_slug"),
]
