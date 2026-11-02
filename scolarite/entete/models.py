from django.db import models
from django.utils.translation import gettext_lazy as _

class Entete(models.Model):
    class Meta:
        db_table = 'entetes'

    nom_fr = models.CharField(_("Nom (Français)"), max_length=200)
    nom_ar = models.CharField(_("الاسم (العربية)"), max_length=200)
    description_fr = models.TextField(_("Description (Français)"), blank=True, null=True)
    description_ar = models.TextField(_("الوصف (العربية)"), blank=True, null=True)
    titre_fr = models.CharField(_("Titre (Français)"), max_length=200, blank=True, null=True)
    titre_ar = models.CharField(_("العنوان (العربية)"), max_length=200, blank=True, null=True)
    titre2_fr = models.CharField(_("Sous-Titre (Français)"), max_length=200, blank=True, null=True)
    titre2_ar = models.CharField(_("العنوان الفرعي (العربية)"), max_length=200, blank=True, null=True)
    logo = models.ImageField(upload_to='logos/', blank=True, null=True, verbose_name=_("Logo"))
