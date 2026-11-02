from parametres.managers import AnneeFilteredManager
from django.db import models

from matiers.models import Matiere
from professeur.models import Professeur
from trimestre.models import Trimestre


class Seance(models.Model):
    objects = AnneeFilteredManager('trimestre__annee')
    class Meta:
        db_table = 'seance'

    TYPE_CHOICES = [
        ('cours', 'Cours'),
        ('devoir', 'Devoir'),
        ('examen', 'Examen'),
        ('conference', 'Conférence')
    ]
    matiere = models.ForeignKey(Matiere, on_delete=models.CASCADE)
    professeur = models.ForeignKey(Professeur, on_delete=models.CASCADE)
    date = models.DateField()
    heure_debut = models.TimeField()
    heure_fin = models.TimeField()
    type = models.CharField(max_length=20, choices=TYPE_CHOICES)
    trimestre = models.ForeignKey(Trimestre, on_delete=models.CASCADE)
