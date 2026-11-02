from parametres.managers import AnneeFilteredManager
from django.db import models
from django.utils.translation import gettext_lazy as _
from emploie.models import EmploiDuTemps
from professeur.models import Professeur
from annee.models import Annee
from trimestre.models import Trimestre

class Pointage(models.Model):
    objects = AnneeFilteredManager('annee')
    class Meta:
        db_table = 'pointage'
        verbose_name = _('Pointage')
        verbose_name_plural = _('Pointages')
        unique_together = ('professeur', 'seance', 'date')

    ETAT_CHOICES = [
        ('present', 'Présent'),
        ('absent', 'Absent'),
        ('retard', 'En retard'),
        ('conge', 'Congé'),
    ]

    professeur = models.ForeignKey(Professeur, on_delete=models.CASCADE, verbose_name=_('Professeur'))
    seance = models.ForeignKey(EmploiDuTemps, on_delete=models.CASCADE, null=True, blank=True, verbose_name=_('Séance'))
    date = models.DateField(verbose_name=_('Date'))
    etat = models.CharField(max_length=10, choices=ETAT_CHOICES, verbose_name=_('État'))
    remarques = models.TextField(blank=True, verbose_name=_('Remarques'))
    annee = models.ForeignKey(Annee, on_delete=models.CASCADE, verbose_name=_('Année') , default=1)
    trimestre = models.ForeignKey(Trimestre, on_delete=models.CASCADE, verbose_name=_('Trimestre') , default=1)

    def __str__(self):
        return f"{self.professeur} - {self.date} - {self.etat} - {self.annee} - {self.trimestre}"