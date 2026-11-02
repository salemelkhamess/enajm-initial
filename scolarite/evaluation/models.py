from parametres.managers import AnneeFilteredManager
from django.db import models

from branches.models import Secteur
from formations.models import Formation
from matiers.models import Matiere
from trimestre.models import Trimestre
from django.utils.translation import gettext_lazy as _

class Evaluation(models.Model):
    objects = AnneeFilteredManager('trimestre__annee')
    class Meta:
        db_table = 'evaluations'

    TYPE_CHOICES = [
        ('devoir', _('Devoir')),
        ('examen', _('Examen'))
    ]



    matiere = models.ForeignKey(Matiere, on_delete=models.CASCADE)
    type = models.CharField(max_length=20, choices=TYPE_CHOICES)
    date = models.DateField()
    coefficient = models.FloatField()
    trimestre = models.ForeignKey(Trimestre, on_delete=models.CASCADE)
    secteur = models.ForeignKey(Secteur, on_delete=models.CASCADE ,default=1)

    def __str__(self):
        return f'{self.trimestre.numero_trimestre}  - {self.trimestre.annee} - {self.type} - {self.secteur.nom} '
