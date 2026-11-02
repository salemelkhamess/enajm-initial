from django.urls import path
from .views import AnneeListView, AnneeCreateView, AnneeUpdateView, AnneeDeleteView

urlpatterns = [
    path('', AnneeListView.as_view(), name='annee_list'),
    path('ajouter/', AnneeCreateView.as_view(), name='annee_create'),
    path('modifier/<int:pk>/', AnneeUpdateView.as_view(), name='annee_edit'),
    path('supprimer/<int:pk>/', AnneeDeleteView.as_view(), name='annee_delete'),
]
