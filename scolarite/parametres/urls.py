# parametres/urls.py
from django.urls import path
from .views import ParametresUpdateView, get_trimestres, set_annee_consultee

urlpatterns = [
    path('', ParametresUpdateView.as_view(), name='update_params'),
    path('get-trim/', get_trimestres, name='parametres_get_trimestres'),
    path('annee-consultee/', set_annee_consultee, name='set_annee_consultee'),
]