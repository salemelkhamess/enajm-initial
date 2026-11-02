from django.urls import path
from . import views

urlpatterns = [
    # URLs pour la gestion des rôles
    path('roles/', views.role_list, name='role_list'),
    path('roles/create/', views.role_create, name='role_create'),
    path('roles/<int:pk>/edit/', views.role_edit, name='role_edit'),
    path('roles/<int:pk>/delete/', views.role_delete, name='role_delete'),

    # URLs pour assigner des rôles aux utilisateurs
    path('users/<int:user_id>/roles/', views.user_roles, name='user_roles'),
    path('users/<int:user_id>/roles/add/', views.add_role_to_user, name='add_role_to_user'),
    path('users/<int:user_id>/roles/<int:role_id>/remove/', views.remove_role_from_user, name='remove_role_from_user'),

]