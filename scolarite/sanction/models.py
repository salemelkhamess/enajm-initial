from parametres.managers import AnneeFilteredManager
from django.db import models

from etudiant.models import Etudiant


class Sanction(models.Model):
    objects = AnneeFilteredManager('etudiant__annee')
    class Meta:
        db_table = 'sanctions'

    etudiant = models.ForeignKey(Etudiant, on_delete=models.CASCADE)
    type = models.CharField(max_length=100)
    description = models.TextField()
    date_sanction = models.DateField()