from django.db import models

from branches.models import Secteur
from formations.models import Formation


class Matiere(models.Model):
    class Meta:
        db_table = 'matiere'

    nom = models.CharField(max_length=100)
    coefficient = models.FloatField()
    secteur = models.ForeignKey(Secteur, on_delete=models.CASCADE,default=1)
    def __str__(self):
        return self.nom
