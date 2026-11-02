from django.db import models
from django.utils.translation import gettext_lazy as _
from formations.models import Formation
from django.utils.translation import gettext_lazy as _

class Secteur(models.Model):
    class Meta:
        db_table = 'secteurs'
        verbose_name = _("Secteur")
        verbose_name_plural = _("Secteurs")

    nom = models.CharField(max_length=100, verbose_name=_("nom"))
    formation = models.ForeignKey(Formation, on_delete=models.CASCADE,
                                related_name='secteurs', verbose_name=_("formation"))

    def __str__(self):
        return f"{self.nom} ({self.formation.nom})"