from django.urls import path, include
from .views import PointageListView, PointageCreateView, PointageUpdateView, load_seances, PointageDeleteView, \
    rapport_absences_detaille, AbsencesProfesseursView

from rest_framework.routers import DefaultRouter
from .api_views import PointageViewSet, PointageListAPIView

router = DefaultRouter()
router.register('pointages', PointageViewSet)

urlpatterns = [
    path('pointages/', PointageListView.as_view(), name='pointage_list'),
    path('pointages/ajouter/', PointageCreateView.as_view(), name='pointage_create'),
    path('pointages/<int:pk>/modifier/', PointageUpdateView.as_view(), name='pointage_update'),
    path('pointages/<int:pk>/supprimer/', PointageDeleteView.as_view(), name='pointage_delete'),

    path('ajax/load-seances/', load_seances, name='ajax_load_seances'),
    path('presence/par-matier/', rapport_absences_detaille, name='presence-par-matier'),
    path('rest/', PointageListAPIView.as_view(), name='api_pointages'),

    path('nouveau/', PointageCreateView.as_view(), name='pointage_create'),
    path('absences-professeurs/', AbsencesProfesseursView.as_view(), name='absences_professeurs'),

]