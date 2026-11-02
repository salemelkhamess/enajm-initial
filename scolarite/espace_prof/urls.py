from django.urls import path

from . import views

urlpatterns = [
    path('', views.accueil, name='espace_prof'),
    path('absences/<int:creneau_id>/', views.absences, name='espace_prof_absences'),
    path('seance/<int:creneau_id>/', views.seance, name='espace_prof_seance'),
    path('notes/', views.notes, name='espace_prof_notes'),
    path('notes/nouvelle/', views.evaluation_nouvelle, name='espace_prof_evaluation_nouvelle'),
    path('notes/<int:evaluation_id>/', views.notes_saisie, name='espace_prof_notes_saisie'),
]
