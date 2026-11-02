from django.urls import path
from .views import PVListView, PVCreateView, PVUpdateView, PVDeleteView, PVRapportView , pv_triche

urlpatterns = [
    path('pvs/', PVListView.as_view(), name='pv_list'),
    path('pvs/create/', PVCreateView.as_view(), name='pv_create'),
    path('pvs/<int:pk>/edit/', PVUpdateView.as_view(), name='pv_edit'),
    path('pvs/<int:pk>/delete/', PVDeleteView.as_view(), name='pv_delete'),
    path('pv/rapport/', PVRapportView.as_view(), name='pv_rapport'),
    path('pvs/triche/<int:pv_id>/', pv_triche, name='pv_triche'),

]
