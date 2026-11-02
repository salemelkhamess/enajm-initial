from django.db import models
from django.utils.translation import gettext_lazy as _

class Salle(models.Model):
    class Meta:
        verbose_name_plural = _("Salles")

    nom = models.CharField(_("Nom"), max_length=100)
    capacite = models.PositiveIntegerField(_("Capacité"))
    description = models.TextField(_("Description"), blank=True, null=True)

    def __str__(self):
        return self.nom
