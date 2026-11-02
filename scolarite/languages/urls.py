from django.urls import path
from . import views

urlpatterns = [
    path('set_language/', views.set_language, name='set_language'),
]
