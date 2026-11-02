from parametres.managers import AnneeFilteredManager
# emploi/models.py
from django.db import models

from annee.models import Annee
from branches.models import Secteur
from matiers.models import Matiere
from parametres.utils import get_annee_courante, get_trimestre_courant
from professeur.models import Professeur
from salle.models import Salle
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _

from trimestre.models import Trimestre
from datetime import datetime, timedelta, date


class EmploiDuTemps(models.Model):
    objects = AnneeFilteredManager('annee')
    JOURS_CHOIX = [
        ('Lundi', _('Lundi')),
        ('Mardi', _('Mardi')),
        ('Mercredi', _('Mercredi')),
        ('Jeudi', _('Jeudi')),
        ('Vendredi', _('Vendredi')),
        ('Samedi', _('Samedi')),
    ]

    secteur = models.ForeignKey(Secteur, on_delete=models.CASCADE)
    matiere = models.ForeignKey(Matiere, on_delete=models.CASCADE)
    professeur = models.ForeignKey(Professeur, on_delete=models.CASCADE)
    salle = models.ForeignKey(Salle, on_delete=models.CASCADE)
    annee = models.ForeignKey(Annee, on_delete=models.CASCADE, verbose_name="Année" )
    trimestre = models.ForeignKey(Trimestre, on_delete=models.CASCADE )
    jour = models.CharField(max_length=10, choices=JOURS_CHOIX)
    heure_debut = models.TimeField()
    heure_fin = models.TimeField()



    class Meta:
        verbose_name = "Emploie"
        verbose_name_plural = "Emplois du temps"
        constraints = [
            models.UniqueConstraint(
                fields=['annee', 'trimestre', 'secteur', 'jour', 'salle', 'heure_debut', 'heure_fin'],
                name='unique_emploi_par_creneau'
            ),
            models.UniqueConstraint(
                fields=['annee', 'trimestre', 'secteur', 'jour', 'professeur', 'heure_debut', 'heure_fin'],
                name='unique_professeur_par_creneau'
            )
        ]



    def clean(self):
        super().clean()

        # Vérifier que l'heure de fin est après l'heure de début
        if self.heure_fin <= self.heure_debut:
            raise ValidationError("L'heure de fin doit être après l'heure de début.")

        # Vérifier que le trimestre appartient à la même année
        if self.trimestre.annee != self.annee:
            raise ValidationError("Le trimestre doit appartenir à la même année.")

        # Vérifier les conflits de salle
        conflits_salle = EmploiDuTemps.objects.filter(
            jour=self.jour,
            salle=self.salle,
            annee=self.annee,
            trimestre=self.trimestre
        ).exclude(
            pk=self.pk if self.pk else None
        ).filter(
            models.Q(
                heure_debut__lt=self.heure_fin,
                heure_fin__gt=self.heure_debut
            )
        )

        if conflits_salle.exists():
            raise ValidationError("La salle est déjà occupée pendant cette plage horaire.")

        # Vérifier les conflits de professeur
        conflits_prof = EmploiDuTemps.objects.filter(
            jour=self.jour,
            professeur=self.professeur,
            annee=self.annee,
            trimestre=self.trimestre
        ).exclude(
            pk=self.pk if self.pk else None
        ).filter(
            models.Q(
                heure_debut__lt=self.heure_fin,
                heure_fin__gt=self.heure_debut
            )
        )

        if conflits_prof.exists():
            raise ValidationError("Le professeur a déjà un cours pendant cette plage horaire.")

    def __str__(self):
        return f"{self.trimestre} - {self.jour} {self.heure_debut} - {self.matiere.nom} ({self.secteur})"



    def save(self, *args, **kwargs):
        self.full_clean()  # Appelle la méthode clean() avant la sauvegarde
        super().save(*args, **kwargs)

    @classmethod
    def get_seances_par_jour(cls, date=None):
        """
        Récupère le nombre de séances pour un jour donné.
        Si aucune date n'est fournie, utilise la date du jour.
        """
        if date is None:
            date = datetime.now().date()

        # Correspondance des jours en français
        jours_fr = {
            0: 'Lundi',
            1: 'Mardi',
            2: 'Mercredi',
            3: 'Jeudi',
            4: 'Vendredi',
            5: 'Samedi',
            6: 'Dimanche'
        }

        jour_semaine = jours_fr[date.weekday()]

        return cls.objects.filter(
            jour=jour_semaine,
            annee=get_annee_courante(),
            trimestre=get_trimestre_courant()
        ).count()

    @classmethod
    def get_seances_par_semaine(cls, date_reference=None):
        """
        Compte toutes les séances pour la semaine scolaire contenant la date donnée.
        Si aucune date n'est fournie, utilise la semaine courante.

        Args:
            date_reference (date, optional): Date quelconque dans la semaine. Defaults à aujourd'hui.

        Returns:
            int: Nombre total de séances pour la semaine
        """
        # 1. Déterminer la date de référence
        if date_reference is None:
            date_reference = datetime.now().date()

        # 2. Calculer le lundi de la semaine (0=Monday)
        lundi = date_reference - timedelta(days=date_reference.weekday())

        # 3. Générer tous les jours de la semaine scolaire (lundi à samedi)
        jours_semaine = [lundi + timedelta(days=i) for i in range(6)]

        # 4. Correspondance des jours en français
        jours_fr = ['Lundi', 'Mardi', 'Mercredi', 'Jeudi', 'Vendredi', 'Samedi']

        # 5. Récupérer l'année et trimestre courants
        annee_courante = get_annee_courante()
        trimestre_courant = get_trimestre_courant()

        if not annee_courante or not trimestre_courant:
            return 0

        # 6. Requête optimisée
        return cls.objects.filter(
            jour__in=jours_fr,
            annee=annee_courante,
            trimestre=trimestre_courant
        ).count()

    @classmethod
    def get_seances_par_mois(cls, annee=None, mois=None):
        """
        Compte toutes les séances pour un mois donné en calculant le nombre réel de semaines.
        """
        aujourdhui = datetime.now().date()
        if annee is None:
            annee = aujourdhui.year
        if mois is None:
            mois = aujourdhui.month

        # 1. Trouver le premier et dernier jour du mois
        premier_jour = date(annee, mois, 1)
        dernier_jour = date(annee, mois + 1, 1) - timedelta(days=1) if mois < 12 else date(annee + 1, 1, 1) - timedelta(
            days=1)

        # 2. Calculer le nombre de semaines complètes
        jours_dans_mois = (dernier_jour - premier_jour).days + 1
        semaines_dans_mois = jours_dans_mois // 7  # Nombre de semaines complètes

        # 3. Multiplier par le nombre de séances hebdomadaires
        seances_par_semaine = cls.get_seances_par_semaine()
        return seances_par_semaine * semaines_dans_mois