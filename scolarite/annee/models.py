from django.db import models
from django.utils.translation import gettext_lazy as _
from formations.models import Formation

class Annee(models.Model):
    class Meta:
        db_table = 'annees'
        verbose_name = _('Année')
        verbose_name_plural = _('Années')

    formation = models.ForeignKey(Formation, on_delete=models.CASCADE, verbose_name=_('formation'))
    numero_annee = models.PositiveIntegerField(verbose_name=_('numero_annee'))

    def __str__(self):
        return f"{self.numero_annee} - {self.numero_annee + 1}"