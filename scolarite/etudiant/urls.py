from django.urls import path
from .views import (
    EtudiantListView, EtudiantCreateView,
    EtudiantUpdateView, EtudiantDeleteView, AttestationView, EtudiantRegistrationView, liste_etudiants_par_secteur,
    get_trimestres, attestation_inscription, carte_etudiant, EtudiantsParSecteurListView, rapport_absence_etudiants,
    AbsencesEtudiantView
)

urlpatterns = [
    path('', EtudiantListView.as_view(), name='etudiant_list'),
    path('ajouter/', EtudiantCreateView.as_view(), name='etudiant_create'),
    path('modifier/<int:pk>/', EtudiantUpdateView.as_view(), name='etudiant_edit'),
    path('supprimer/<int:pk>/', EtudiantDeleteView.as_view(), name='etudiant_delete'),
    path('etudiant/<int:pk>/attestation/', AttestationView.as_view(), name='etudiant_attestation'),
    path('etudiant/<int:pk>/registration/', EtudiantRegistrationView.as_view(), name='etudiant_registration'),
    path('liste-par-secteur/', liste_etudiants_par_secteur, name='liste_par_secteur'),
    path('get-trimestres/', get_trimestres, name='get_trimestres'),

    path('etudiant/<int:etudiant_id>/attestation/nscription/', attestation_inscription, name='nscription'),
    path('carte-etudiant/<str:matricule>/', carte_etudiant, name='carte_etudiant'),
    path('etudiants/secteur/<int:secteur_id>/',
         EtudiantsParSecteurListView.as_view(),
         name='etudiants_par_secteur'),
    path('rapport-absence-etudiants/', rapport_absence_etudiants, name='rapport_absence_etudiants'),
    path('etudiant/<int:pk>/absences/', AbsencesEtudiantView.as_view(), name='absences_etudiant'),
]
