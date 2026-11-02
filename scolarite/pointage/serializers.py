# pointages/serializers.py
from rest_framework import serializers
from .models import Pointage


class PointageSerializer(serializers.ModelSerializer):
    professeur_nom = serializers.CharField(source='professeur.nom', read_only=True)
    professeur_prenom = serializers.CharField(source='professeur.prenom', read_only=True)
    matiere = serializers.CharField(source='seance.matiere.nom', read_only=True)

    class Meta:
        model = Pointage
        fields = ['id', 'professeur_nom', 'professeur_prenom', 'date', 'etat', 'remarques', 'matiere']