# urls.py
from django.urls import path
from .views import FormationListView, FormationCreateView, FormationUpdateView, FormationDeleteView

urlpatterns = [
    path('', FormationListView.as_view(), name='formation_list'),
    path('ajouter/', FormationCreateView.as_view(), name='formation_create'),
    path('modifier/<int:pk>/', FormationUpdateView.as_view(), name='formation_edit'),
    path('supprimer/<int:pk>/', FormationDeleteView.as_view(), name='formation_delete'),
]
