from django.contrib import admin
from django.urls import path, include
from django.views.generic import RedirectView
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path("admin/", admin.site.urls),

    # Visi detaliu_registras keliai po /detaliu_registras/
    path(
        "detaliu_registras/",
        include(("detaliu_registras.urls", "detaliu_registras"), namespace="detaliu_registras"),
    ),

    # Patogus nukreipimas iš šaknies į sąrašą (neprivaloma)
    path("", RedirectView.as_view(pattern_name="detaliu_registras:uzklausa_list", permanent=False)),
]

# Tik DEV aplinkai: statinių ir media failų paduotis
if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
    if getattr(settings, "MEDIA_URL", None) and getattr(settings, "MEDIA_ROOT", None):
        urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
