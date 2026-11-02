from parametres.managers import AnneeFilteredManager
from django.db import models

from emploie.models import EmploiDuTemps


class Permutation(models.Model):
    objects = AnneeFilteredManager('emploi_temps1__annee')
    class Meta:
        db_table = 'permutations'

    emploi_temps1 = models.ForeignKey(EmploiDuTemps, related_name='permutation1', on_delete=models.CASCADE)
    emploi_temps2 = models.ForeignKey(EmploiDuTemps, related_name='permutation2', on_delete=models.CASCADE)
    date_permutation = models.DateField()
    raison = models.TextField()