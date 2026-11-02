# urls.py
from django.urls import path
from . import views
from .views import note_par_evaluation, note_par_evaluation_edit

urlpatterns = [
    path('notes/', views.note_list, name='note_list'),
    path('notes/create/', views.note_create, name='note_create'),
    path('notes/update/<int:pk>/', views.note_update, name='note_update'),
    path('notes/delete/<int:pk>/', views.note_delete, name='note_delete'),
    path('notes/evaluation/', views.note_par_evaluation, name='note_par_evaluation'),
    path('bulletin/', views.afficher_bulletin, name='afficher_bulletin'),
    path('notes-speciales/', views.gestion_notes_speciales, name='gestion_notes_speciales'),
    path('notes/edition/', note_par_evaluation_edit, name='edition_notes'),

]
