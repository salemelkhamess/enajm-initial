from django.db import models
from annee.models import Annee

from django.utils import translation
from django.utils.translation import gettext_lazy as _

class Trimestre(models.Model):
    class Meta:
        db_table = 'trimestres'
        verbose_name = _("Trimestre")
        verbose_name_plural = _("Trimestres")

    annee = models.ForeignKey(Annee, on_delete=models.CASCADE, verbose_name=_("Année"))
    numero_trimestre = models.PositiveIntegerField(verbose_name=_("Numéro"))
    debut = models.DateField(verbose_name=_("Début"))
    fin = models.DateField(verbose_name=_("Fin"))
    nom_fr = models.CharField(max_length=100, verbose_name=_("Nom (Français)"), default="Prémiére trimestre")
    nom_ar = models.CharField(max_length=100, verbose_name=_("Nom (Arabe)"), default="Prémiére trimestre")

    @property
    def nom(self):
        """Nom du trimestre dans la langue active."""
        if (translation.get_language() or '').startswith('ar') and self.nom_ar:
            return self.nom_ar
        return self.nom_fr

    def __str__(self):
        return f"{self.nom} - {self.annee}"
