from django.urls import path
from .views import DocumentListView, DocumentCreateView, DocumentUpdateView, DocumentDeleteView

urlpatterns = [
    path('etudiant/<int:etudiant_id>/documents/', DocumentListView.as_view(), name='document_list'),
    path('etudiant/<int:etudiant_id>/documents/ajouter/', DocumentCreateView.as_view(), name='document_create'),
    path('documents/<int:pk>/modifier/', DocumentUpdateView.as_view(), name='document_update'),
    path('documents/<int:pk>/supprimer/', DocumentDeleteView.as_view(), name='document_delete'),
]