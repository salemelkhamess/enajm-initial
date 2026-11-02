from django.db import models

from matiers.models import Matiere
from professeur.models import Professeur

class PresenceProfesseur(models.Model):
    class Meta:
        db_table = 'presence_professeur'

    professeur = models.ForeignKey(Professeur, on_delete=models.CASCADE)
    matiere = models.ForeignKey(Matiere, on_delete=models.CASCADE,default=1)
    present = models.BooleanField(default=True)
    justification = models.TextField(blank=True, null=True)
    date_justification = models.DateField(blank=True, null=True)

