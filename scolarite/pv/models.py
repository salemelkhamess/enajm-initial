from parametres.managers import AnneeFilteredManager
from django.db import models
from etudiant.models import Etudiant
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from annee.models import Annee
from matiers.models import Matiere
from trimestre.models import Trimestre


class PV(models.Model):
    objects = AnneeFilteredManager('annee')
    # Choix pour le type de PV
    TYPES = [
        ('triche', _('Triche')),
        ('absence', _('Absence')),
        ('retard', _('Retard')),
        ('autre', _('Autre')),
    ]

    # Choix pour les jours de la semaine
    JOURS_CHOIX = [
        ('Lundi', _('Lundi')),
        ('Mardi', _('Mardi')),
        ('Mercredi', _('Mercredi')),
        ('Jeudi', _('Jeudi')),
        ('Vendredi', _('Vendredi')),
        ('Samedi', _('Samedi')),
    ]

    type = models.CharField(
        max_length=50,
        choices=TYPES,
        verbose_name=_("Type de PV")
    )
    etudiant = models.ForeignKey(
        Etudiant,
        on_delete=models.CASCADE,
        verbose_name=_("Étudiant"),
        related_name='pvs'
    )
    matiere = models.ForeignKey(
        Matiere,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name=_("Matière"),
        related_name='pvs'
    )
    contenu = models.TextField(verbose_name=_("Contenu"))

    # Champs académiques
    annee = models.ForeignKey(
        Annee,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name=_("Anne")
    )
    trimestre = models.ForeignKey(
        Trimestre,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name=_("Trimestre")
    )
    jour_semaine = models.CharField(
        max_length=10,
        choices=JOURS_CHOIX,
        verbose_name=_("Jour"),
        null=True,
        blank=True
    )
    date_incident = models.DateField(
        default=timezone.now,
        verbose_name=_("Date")
    )
    date_creation = models.DateTimeField(
        auto_now_add=True,
        verbose_name=_("Date")
    )

    class Meta:
        db_table = 'pvs'
        verbose_name = _("Procès-verbal")
        verbose_name_plural = _("Procès-verbaux")
        ordering = ['-date_incident']

    def __str__(self):
        return f"{self.get_type_display()} - {self.etudiant} - {self.matiere or 'Aucune matière'}"

    def save(self, *args, **kwargs):
        """Détermine automatiquement le jour de la semaine si non spécifié"""
        if not self.jour_semaine and self.date_incident:
            jours = ['Lundi', 'Mardi', 'Mercredi', 'Jeudi', 'Vendredi', 'Samedi', 'Dimanche']
            jour_index = self.date_incident.weekday()
            if jour_index < len(jours):  # On ignore Dimanche (index 6)
                self.jour_semaine = jours[jour_index]
        super().save(*args, **kwargs)