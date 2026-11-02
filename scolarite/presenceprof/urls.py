# urls.py
from django.urls import path
from .views import *

urlpatterns = [
    path('presences/', PresenceListView.as_view(), name='presence_list'),
    path('presences/ajouter/', PresenceCreateView.as_view(), name='presence_create'),
    path('presences/<int:pk>/modifier/', PresenceUpdateView.as_view(), name='presence_update'),
    path('presences/<int:pk>/supprimer/', PresenceDeleteView.as_view(), name='presence_delete'),
    path('rapport-presences/', rapport_presence_professeurs, name='rapport_presence_professeurs'),

]
