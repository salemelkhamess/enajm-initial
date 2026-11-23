from django.db import models
from django.utils import translation
from django.utils.translation import gettext_lazy as _


class Niveau(models.Model):
    """
    Niveau de langue d'un élève fonctionnaire (paramétrable). Il servira à regrouper des élèves de secteurs
    différents (cours de langue arabe / française, salles, emploi du temps, devoirs, examens).
    Un niveau ne se supprime pas : on le désactive (il n'est alors plus proposé).
    """
    nom_fr = models.CharField(_("Nom (français)"), max_length=100, unique=True)
    nom_ar = models.CharField(_("Nom (arabe)"), max_length=100, unique=True)
    actif = models.BooleanField(_("Actif"), default=True)

    class Meta:
        db_table = 'niveaux'
        verbose_name = _("Niveau")
        verbose_name_plural = _("Niveaux")
        ordering = ['nom_fr']

    @property
    def nom(self):
        """Nom dans la langue active (avec repli sur l'autre langue)."""
        if (translation.get_language() or '').startswith('ar'):
            return self.nom_ar or self.nom_fr
        return self.nom_fr or self.nom_ar

    @property
    def libelle(self):
        """Nom bilingue « arabe / français » pour les listes de choix."""
        return f"{self.nom_ar} / {self.nom_fr}"

    def __str__(self):
        return self.nom

    @classmethod
    def actifs(cls):
        return cls.objects.filter(actif=True)

    def delete(self, *args, **kwargs):
        raise models.ProtectedError(_("Un niveau ne se supprime pas : désactivez-le."), {self})
