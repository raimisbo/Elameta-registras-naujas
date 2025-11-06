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

    # Pagrindinis app su namespace 'detaliu_registras'
    path(
        "detaliu_registras/",
        include(("detaliu_registras.urls", "detaliu_registras"), namespace="detaliu_registras"),
    ),

    # Istorijos maršrutai (jei naudoji istorijos partialus šablonuose)
    path(
        "detaliu_registras/",
        include(("detaliu_registras.urls_history", "detaliu_registras_history"), namespace="detaliu_registras_history"),
    ),
    path("pozicijos/", include(("pozicijos.urls", "pozicijos"), namespace="pozicijos")),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
