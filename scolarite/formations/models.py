from django.db import models

class Formation(models.Model):
    class Meta:
        db_table = 'formations'

    nom = models.CharField(max_length=100)
    nom_fr = models.CharField("Nom (français)", max_length=150, blank=True, default='')

    @property
    def nom_francais(self):
        return self.nom_fr or self.nom

    @property
    def nom_affiche(self):
        """Nom dans la langue de l'interface (français : nom français s'il existe)."""
        from django.utils import translation
        return self.nom if (translation.get_language() or '').startswith('ar') else self.nom_francais

    def __str__(self):
        return self.nom