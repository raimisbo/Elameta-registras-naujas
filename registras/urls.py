# registras/urls.py
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path("admin/", admin.site.urls),

    # Visi maršrutai iš app'o 'detaliu_registras'
    # Naudojame namespace 'detaliu_registras', kad šablonuose veiktų {% url 'detaliu_registras:...' %}
    path(
        "detaliu_registras/",
        include(("detaliu_registras.urls", "detaliu_registras"), namespace="detaliu_registras"),
    ),
    path('detaliu_registras/', include('detaliu_registras.urls_history')),
]

# Vystymo režime patiekiam media failus (pvz. įkeltus brėžinius, dokumentus)
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
