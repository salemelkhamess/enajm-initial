from django.urls import path
from .views import (
    EvaluationListView, EvaluationCreateView,
    EvaluationUpdateView, EvaluationDeleteView , load_trimestres , EvaluationCreateFormView
)

urlpatterns = [
    path('', EvaluationListView.as_view(), name='evaluation_list'),
    path('ajouter/', EvaluationCreateView.as_view(), name='evaluation_create'),
    path('modifier/<int:pk>/', EvaluationUpdateView.as_view(), name='evaluation_update'),
    path('supprimer/<int:pk>/', EvaluationDeleteView.as_view(), name='evaluation_delete'),
    path('ajax/load-trimestres/', load_trimestres, name='load_trimestres'),

    path('formulaire-presence/', EvaluationCreateFormView.as_view(), name='formulaire-presence'),

]
