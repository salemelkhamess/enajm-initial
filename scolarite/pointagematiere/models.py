from parametres.managers import AnneeFilteredManager
from django.db import models
from django.utils.translation import gettext_lazy as _
from branches.models import Secteur
from annee.models import Annee
from matiers.models import Matiere
from professeur.models import Professeur
from trimestre.models import Trimestre

class PointageMatiere(models.Model):
    objects = AnneeFilteredManager('annee')
    class Etat(models.TextChoices):
        EFFECTUE = 'EF', _('Effectué')
        ANNULE = 'AN', _('Annulé')
        REPORTE = 'RP', _('Reporté')

    class Meta:
        db_table = 'pointage_matieres'
        verbose_name = _("Pointage matière")
        verbose_name_plural = _("Pointages matières")
        ordering = ['-date_cours']
        constraints = [
            models.CheckConstraint(
                check=models.Q(heure_fin__gt=models.F('heure_debut')),
                name='heure_fin_apres_heure_debut'
            )
        ]

    annee = models.ForeignKey(Annee, on_delete=models.CASCADE, verbose_name=_("Année"))
    trimestre = models.ForeignKey(Trimestre, on_delete=models.CASCADE, verbose_name=_("Trimestre"))
    secteur = models.ForeignKey(Secteur, on_delete=models.CASCADE, verbose_name=_("Secteur"))
    matiere = models.ForeignKey(Matiere, on_delete=models.CASCADE, verbose_name=_("Matière"))
    professeur = models.ForeignKey(Professeur, on_delete=models.CASCADE, verbose_name=_("Professeur"))
    date_cours = models.DateField(verbose_name=_("Date du cours"))
    heure_debut = models.TimeField(verbose_name=_("Heure de début"))
    heure_fin = models.TimeField(verbose_name=_("Heure de fin"))
    etat = models.CharField(
        max_length=2,
        choices=Etat.choices,
        default=Etat.EFFECTUE,
        verbose_name=_("État")
    )
    contenu = models.TextField(verbose_name=_("Contenu enseigné"), blank=True, null=True)
    remarques = models.TextField(verbose_name=_("Remarques"), blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.matiere} - {self.date_cours} ({self.get_etat_display()})"

    def duree(self):
        """Calcule la durée du cours en heures"""
        from datetime import datetime
        debut = datetime.combine(self.date_cours, self.heure_debut)
        fin = datetime.combine(self.date_cours, self.heure_fin)
        return (fin - debut).total_seconds() / 3600  # Convertir en heures

    def est_termine(self):
        """Vérifie si le cours est terminé (état Effectué)"""
        return self.etat == self.Etat.EFFECTUE

    def est_a_venir(self):
        """Vérifie si le cours est à venir (état Planifié)"""
        return self.etat == self.Etat.EFFECTUE