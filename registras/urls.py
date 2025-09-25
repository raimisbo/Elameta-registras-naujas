# registras/urls.py
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.views.generic import RedirectView

urlpatterns = [
    path("admin/", admin.site.urls),

    # Visi maršrutai iš app'o 'detaliu_registras'
    # Naudojame namespace 'detaliu_registras', kad šablonuose veiktų {% url 'detaliu_registras:...' %}
    path(
        "detaliu_registras/",
        include(("detaliu_registras.urls", "detaliu_registras"), namespace="detaliu_registras"),
    ),
    path("", RedirectView.as_view(pattern_name="detaliu_registras:uzklausa_list", permanent=False)),
]

# Vystymo režime patiekiam media failus (pvz. įkeltus brėžinius, dokumentus)
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
