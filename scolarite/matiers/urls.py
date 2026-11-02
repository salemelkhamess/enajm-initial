from django.urls import path
from .views import MatiereListView, MatiereCreateView, MatiereUpdateView, MatiereDeleteView

urlpatterns = [
    path('', MatiereListView.as_view(), name='matiere_list'),
    path('ajouter/', MatiereCreateView.as_view(), name='matiere_create'),
    path('modifier/<int:pk>/', MatiereUpdateView.as_view(), name='matiere_edit'),
    path('supprimer/<int:pk>/', MatiereDeleteView.as_view(), name='matiere_delete'),
]
