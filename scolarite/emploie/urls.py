# emploi/urls.py
from django.urls import path
from .views import EmploiListView, EmploiCreateView, EmploiUpdateView, EmploiDeleteView, emploi_par_secteur, \
    EmploiGrilleView, SauvegarderGrilleView, load_trimestres, EmploiGrilleEditView

urlpatterns = [
    path('', EmploiListView.as_view(), name='emploi_liste'),
    path('ajouter/', EmploiCreateView.as_view(), name='emploi_create'),
    path('<int:pk>/modifier/', EmploiUpdateView.as_view(), name='emploi_update'),
    path('<int:pk>/supprimer/', EmploiDeleteView.as_view(), name='emploi_delete'),
    path('emploi-secteur/', emploi_par_secteur, name='emploi_par_secteur'),
path('emploi/grille/', EmploiGrilleView.as_view(), name='emploi_grille'),
path('emploi/sauvegarder-grille/', SauvegarderGrilleView.as_view(), name='sauvegarder_grille'),
path('ajax/load-trimestres/', load_trimestres, name='load_trimestres'),
    # Nouvelle URL pour l'édition par grille
    path('grille-edition/<int:pk>/', EmploiGrilleEditView.as_view(), name='emploi_grille_edit'),

]


