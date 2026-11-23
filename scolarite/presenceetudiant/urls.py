from django.urls import path

from emploie.views import load_trimestres
from . import views
from .views import rapport_absences, PresenceSelectionView, PresenceSaisieView, EnregistrerPresenceView, \
    PresenceEtudiantUpdateView, load_matieres, GestionPresenceView, charger_matieres, EnregistrerPresenceViewH, \
    EnregistrementPresenceView, EnregistrementPresenceEtudiantsView, matieres_api, rapport_absences_by_class, \
    liste_absences_non_justifiees, modifier_statut_absence, AbsenceParMatiereView

urlpatterns = [
    path('', views.PresenceEtudiantListView.as_view(), name='presence_liste'),
    path('ajouter/', views.PresenceEtudiantCreateView.as_view(), name='presence_createe'),
   path('modifier/<int:pk>/', views.PresenceEtudiantUpdateView.as_view(), name='presence_updatee'),
    path('supprimer/<int:pk>/', views.PresenceEtudiantDeleteView.as_view(), name='presence_deletee'),
    path('rapport/absences/', rapport_absences, name='rapport_absences'),
    path('selection/', PresenceSelectionView.as_view(), name='presence_selection'),
    path('saisie/', PresenceSaisieView.as_view(), name='presence_saisie'),
    path('ajax/load-trimestres/', load_trimestres, name='load_trimestres'),
    path('presence/enregistrer/', EnregistrerPresenceView.as_view(), name='enregistrer_presence'),
  #  path('modifier/<int:pk>/', PresenceEtudiantUpdateView.as_view(), name='presence_updatee'),
    path('selection/ph/', views.GestionPresenceView.as_view(), name='selection'),
    path('enregistrer/pre/', views.EnregistrerPresenceViewH.as_view(), name='enregistrer'),
    path('ajax/charger-matieres/', views.charger_matieres, name='charger_matieres'),

    path('enregistrement-presence/', EnregistrementPresenceView.as_view(), name='enregistrement_presence'),
    path('groupes-classe/', views.groupes_classe_api, name='groupes_classe_api'),
    path('listes-pointage/', views.listes_pointage, name='listes_pointage'),
    path('listes-pointage/imprimer/', views.listes_pointage_imprimer, name='listes_pointage_imprimer'),
    path('enregistrement-presence/etudiants/', EnregistrementPresenceEtudiantsView.as_view(),
         name='enregistrement_presence_etudiants'),
    path('matieres/', matieres_api, name='matieres_api'),
path('rapport-absences-classe/', rapport_absences_by_class, name='rapport_absences_classe'),

    path('absences/non-justifiees/', liste_absences_non_justifiees, name='liste_absences_non_justifiees'),
    path('absences/modifier/<int:absence_id>/', modifier_statut_absence, name='modifier_statut_absence'),
    path('absences_non_justifiees/', views.absences_non_justifiees, name='absences_non_justifiees'),
    path('absence-alerts/', views.check_absence_alerts, name='absence_alerts'),
    path('absences/valider/<int:absence_id>/', views.valider_absence, name='valider_absence'),
    path('absences/examiner/<int:absence_id>/', views.examiner_justification, name='examiner_justification'),
    path('absences/periode/', views.justification_periode, name='justification_periode'),
    path('absences/historique/', views.historique_justifications_general, name='historique_justifications_general'),
    path('absences/historique/<int:etudiant_id>/', views.historique_justifications, name='historique_justifications'),
    path('absences/periode/<int:periode_id>/examiner/', views.examiner_periode, name='examiner_periode'),
    path('absences/justificatif/<int:document_id>/', views.justificatif_document, name='justificatif_document'),
    path('absences-par-matiere/', AbsenceParMatiereView.as_view(), name='absences_par_matiere'),

]
