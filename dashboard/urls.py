from django.urls import path
from . import views

urlpatterns = [
    path('', views.index, name='dashboard'),
    path('api/filas/', views.estado_filas, name='estado_filas'),
    path('api/stats/', views.estatisticas, name='estatisticas'),
    path('api/medicos/', views.listar_medicos, name='api_medicos'),
]
