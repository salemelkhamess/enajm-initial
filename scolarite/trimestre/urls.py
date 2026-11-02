from django.urls import path
from .views import TrimestreListView, TrimestreCreateView, TrimestreUpdateView, TrimestreDeleteView

urlpatterns = [
    path('trimestres/', TrimestreListView.as_view(), name='trimestre_list'),
    path('trimestres/create/', TrimestreCreateView.as_view(), name='trimestre_create'),
    path('trimestres/<int:pk>/edit/', TrimestreUpdateView.as_view(), name='trimestre_edit'),
    path('trimestres/<int:pk>/delete/', TrimestreDeleteView.as_view(), name='trimestre_delete'),
]
