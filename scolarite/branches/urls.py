from django.urls import path
from .views import (
    SecteurListView, SecteurCreateView,
    SecteurUpdateView, SecteurDeleteView
)

urlpatterns = [
    path('branches/', SecteurListView.as_view(), name='secteur_list'),
    path('branches/ajouter/', SecteurCreateView.as_view(), name='secteur_create'),
    path('branches/modifier/<int:pk>/', SecteurUpdateView.as_view(), name='secteur_update'),
    path('branches/supprimer/<int:pk>/', SecteurDeleteView.as_view(), name='secteur_delete'),
]