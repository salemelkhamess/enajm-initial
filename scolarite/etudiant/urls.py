from django.urls import path
from .views import (
    EtudiantListView, EtudiantCreateView,
    EtudiantUpdateView, EtudiantDeleteView, AttestationView, EtudiantRegistrationView, liste_etudiants_par_secteur,
    get_trimestres, attestation_inscription, carte_etudiant, cartes_etudiants, photo_carte, EtudiantsParSecteurListView, rapport_absence_etudiants,
    AbsencesEtudiantView, liste_etudiants_imprimer, exporter_etudiants_excel, importer_etudiants_excel,
    modele_import_excel, exporter_liste_simple_excel
)

urlpatterns = [
    path('', EtudiantListView.as_view(), name='etudiant_list'),
    path('ajouter/', EtudiantCreateView.as_view(), name='etudiant_create'),
    path('modifier/<int:pk>/', EtudiantUpdateView.as_view(), name='etudiant_edit'),
    path('supprimer/<int:pk>/', EtudiantDeleteView.as_view(), name='etudiant_delete'),
    path('etudiant/<int:pk>/attestation/', AttestationView.as_view(), name='etudiant_attestation'),
    path('etudiant/<int:pk>/registration/', EtudiantRegistrationView.as_view(), name='etudiant_registration'),
    path('liste-par-secteur/', liste_etudiants_par_secteur, name='liste_par_secteur'),
    path('imprimer/', liste_etudiants_imprimer, name='liste_etudiants_imprimer'),
    path('exporter-excel/', exporter_etudiants_excel, name='etudiants_exporter_excel'),
    path('importer-excel/', importer_etudiants_excel, name='etudiants_importer_excel'),
    path('exporter-liste-excel/', exporter_liste_simple_excel, name='etudiants_exporter_liste_excel'),
    path('modele-excel/', modele_import_excel, name='etudiants_modele_excel'),
    path('get-trimestres/', get_trimestres, name='get_trimestres'),

    path('etudiant/<int:etudiant_id>/attestation/nscription/', attestation_inscription, name='nscription'),
    path('carte-etudiant/<str:matricule>/', carte_etudiant, name='carte_etudiant'),
    path('cartes/', cartes_etudiants, name='cartes_etudiants'),
    path('photo-carte/<int:pk>/', photo_carte, name='photo_carte'),
    path('etudiants/secteur/<int:secteur_id>/',
         EtudiantsParSecteurListView.as_view(),
         name='etudiants_par_secteur'),
    path('rapport-absence-etudiants/', rapport_absence_etudiants, name='rapport_absence_etudiants'),
    path('etudiant/<int:pk>/absences/', AbsencesEtudiantView.as_view(), name='absences_etudiant'),
]
