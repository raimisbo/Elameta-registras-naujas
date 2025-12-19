from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.views.generic import RedirectView

urlpatterns = [
    path("admin/", admin.site.urls),

    # / -> senasis užklausų sąrašas
    path(
        "",
        RedirectView.as_view(
            pattern_name="pozicijos:list",
            permanent=False,
        ),
        name="home_redirect",
    ),

    # detaliu_registras yra archyvas – laikom projekte, bet runtime nenaudojam.
    path("pozicijos/", include(("pozicijos.urls", "pozicijos"), namespace="pozicijos")),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
