from django.urls import path
from . import views

urlpatterns = [
    path('', views.index, name='index'),  # Pagrindinis startinis puslapis
    path('ivesti_uzklausa/', views.ivesti_uzklausa, name='ivesti_uzklausa'),
    path('import_csv/', views.import_csv_view, name='import_csv'),
    path('detaliu_registras/uzklausa/redaguoti_kaina/<int:uzklausa_id>/', views.redaguoti_kaina, name='redaguoti_kaina'),
    path('uzklausa/ivesti/<int:uzklausa_id>/', views.ivesti_uzklausa, name='ivesti_uzklausa'),
    path('uzklausos/<int:klientas_id>/', views.perziureti_uzklausas, name='perziureti_uzklausas'),
    path('perziureti_uzklausa/<int:uzklausa_id>/', views.perziureti_uzklausa, name='perziureti_uzklausa'),
    path('perziureti_uzklausa/<int:uzklausa_id>/<path:brėžinio_url>/', views.perziureti_uzklausa, name='perziureti_uzklausa_detailed'),
]