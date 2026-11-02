from django.urls import path
from . import views

urlpatterns = [
    path('entetes/', views.entete_list, name='entete_list'),
    path('entetes/create/', views.entete_create, name='entete_create'),
    path('entetes/<int:pk>/edit/', views.entete_update, name='entete_update'),
    path('entetes/<int:pk>/delete/', views.entete_delete, name='entete_delete'),
]
