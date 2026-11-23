from django.urls import path

from . import views

urlpatterns = [
    path('', views.groupe_liste, name='groupe_liste'),
    path('ajouter/', views.groupe_creer, name='groupe_creer'),
    path('<int:pk>/modifier/', views.groupe_modifier, name='groupe_modifier'),
    path('<int:pk>/eleves/', views.groupe_eleves, name='groupe_eleves'),
    path('<int:pk>/imprimer/', views.groupe_imprimer, name='groupe_imprimer'),
    path('<int:pk>/basculer/', views.groupe_basculer, name='groupe_basculer'),
    path('<int:pk>/supprimer/', views.groupe_supprimer, name='groupe_supprimer'),
]
