from django.db import models

from matiers.models import Matiere
from professeur.models import Professeur


class SeanceNonPrevue(models.Model):
    class Meta:
        db_table = 'seance_non_prevue'

    matiere = models.ForeignKey(Matiere, on_delete=models.CASCADE)
    professeur = models.ForeignKey(Professeur, on_delete=models.CASCADE)
    date = models.DateField()
    heure_debut = models.TimeField()
    heure_fin = models.TimeField()
    raison = models.TextField()