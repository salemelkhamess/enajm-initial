# urls.py
from django.urls import path
from .views import (
    ProfesseurListView,
    ProfesseurCreateView,
    ProfesseurUpdateView,
    ProfesseurDeleteView, certificat_enseignement
)

urlpatterns = [
    path('professeurs/', ProfesseurListView.as_view(), name='professeur_list'),
    path('professeurs/ajouter/', ProfesseurCreateView.as_view(), name='professeur_create'),
    path('professeurs/<int:pk>/modifier/', ProfesseurUpdateView.as_view(), name='professeur_update'),
    path('professeurs/<int:pk>/supprimer/', ProfesseurDeleteView.as_view(), name='professeur_delete'),
    path('professeur/certificat/<int:pk>/', certificat_enseignement, name='professeur_certificat'),]
