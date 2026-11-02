from django.urls import path
from .views import (
    PointageMatiereListView,
    PointageMatiereCreateView,
    PointageMatiereUpdateView,
    PointageMatiereDeleteView,
get_trimestres,
get_matieres,
RapportPointageListView
)

urlpatterns = [
    path('', PointageMatiereListView.as_view(), name='pointage_matiere_list'),
    path('ajouter/', PointageMatiereCreateView.as_view(), name='pointage_matiere_create'),
    path('<int:pk>/modifier/', PointageMatiereUpdateView.as_view(), name='pointage_matiere_update'),
    path('<int:pk>/supprimer/', PointageMatiereDeleteView.as_view(), name='pointage_matiere_delete'),
path('api/get-trimestres/', get_trimestres, name='get_trimestres'),
path('api/get-matieres/',get_matieres, name='get_matieres'),
    path('rapport-pointages/', RapportPointageListView.as_view(), name='rapport_pointages'),

]