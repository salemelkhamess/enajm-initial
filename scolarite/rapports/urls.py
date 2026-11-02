from django.urls import path

from . import views

urlpatterns = [
    path('absences-etudiants/', views.recap_absences_etudiants, name='recap_absences_etudiants'),
    path('horaires-professeurs/', views.horaires_absences_professeurs, name='horaires_absences_professeurs'),
    path('heures-cours/', views.heures_cours_par_trimestre, name='heures_cours_trimestre'),
    path('absences-seuils/', views.recap_absences_seuils, name='recap_absences_seuils'),
]
