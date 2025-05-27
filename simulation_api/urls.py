from django.urls import path
from .views import (
    RunUrgencias, RunCliente, SimulateMultiSalas,
    CommandStatus, LogsView
)

urlpatterns = [
    path('runurgencias/', RunUrgencias.as_view(), name='runurgencias'),
    path('runcliente/',  RunCliente.as_view(),  name='runcliente'),
    path('simulate/',    SimulateMultiSalas.as_view(), name='simulate'),
    path('commands/<int:pk>/', CommandStatus.as_view(), name='command-status'),
    path('logs/', LogsView.as_view(), name='logs'),
]