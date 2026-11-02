from parametres.managers import AnneeFilteredManager
from django.db import models

from etudiant.models import Etudiant
from trimestre.models import Trimestre


class Bulletin(models.Model):
    objects = AnneeFilteredManager('trimestre__annee')
    class Meta:
        db_table = 'bullets'
    etudiant = models.ForeignKey(Etudiant, on_delete=models.CASCADE)
    trimestre = models.ForeignKey(Trimestre, on_delete=models.CASCADE)
    moyenne_generale = models.FloatField()
    classement = models.PositiveIntegerField()
    mention = models.CharField(max_length=50)