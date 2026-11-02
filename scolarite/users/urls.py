from django.urls import path
from . import views
from .views import UserListView, UserCreateView, UserUpdateView, deactivate_user, profile_view

urlpatterns = [
    path('users/', UserListView.as_view(), name='user_list'),
    path('users/create/', UserCreateView.as_view(), name='user_create'),

    path('users/<int:pk>/edit/', UserUpdateView.as_view(), name='user_edit'),
    path('users/<int:pk>/deactivate/', deactivate_user, name='user_deactivate'),

    path('users/<int:pk>/update/', views.user_update, name='user_update'),
    path('users/<int:pk>/delete/', views.user_delete, name='user_delete'),
    path('groups/', views.group_list, name='group_list'),  # Afficher tous les groupes
    path('groups/create/', views.group_create, name='group_create'),  # Créer un groupe
    path('groups/edit/<int:group_id>/', views.group_edit, name='group_edit'),  # Modifier un groupe
    path('groups/delete/<int:group_id>/', views.group_delete, name='group_delete'),  # Supprimer un groupe
    path('profile/', profile_view, name='profile_view'),

]
