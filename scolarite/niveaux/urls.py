from django.urls import path

from . import views

urlpatterns = [
    path('', views.niveau_liste, name='niveau_liste'),
    path('ajouter/', views.niveau_creer, name='niveau_creer'),
    path('<int:pk>/modifier/', views.niveau_modifier, name='niveau_modifier'),
    path('<int:pk>/basculer/', views.niveau_basculer, name='niveau_basculer'),
]
