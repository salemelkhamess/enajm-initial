from django.urls import path
from . import views

urlpatterns = [
    path('salles/', views.salle_list, name='salle_list'),
    path('salles/create/', views.salle_create, name='salle_create'),
    path('salles/<int:pk>/edit/', views.salle_update, name='salle_update'),
    path('salles/<int:pk>/delete/', views.salle_delete, name='salle_delete'),
]
