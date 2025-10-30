from django.urls import path
from . import views

app_name = "pozicijos"

urlpatterns = [
    path("", views.PozicijuSarasasView.as_view(), name="list"),
    path("tbody/", views.PozicijuTbodyPartialView.as_view(), name="tbody"),
    path("detale/<slug:slug>/", views.PozicijosKorteleView.as_view(), name="detail"),
    path("stats/", views.PozicijuStatsView.as_view(), name="stats"),
    path("<int:pk>/", views.PozicijaDetailView.as_view(), name="detail"),
]
