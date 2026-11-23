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
    nom_fr = models.CharField(max_length=150, blank=True, default='', verbose_name=_("Nom (français)"))
    formation = models.ForeignKey(Formation, on_delete=models.CASCADE,
                                related_name='secteurs', verbose_name=_("formation"))

    @property
    def nom_francais(self):
        """Nom de la classe en français (à défaut : le nom arabe)."""
        return self.nom_fr or self.nom

    @property
    def nom_affiche(self):
        """Nom dans la langue de l'interface : arabe en arabe, français en français."""
        from django.utils import translation
        return self.nom if (translation.get_language() or '').startswith('ar') else self.nom_francais

    def __str__(self):
        return f"{self.nom} ({self.formation.nom})"