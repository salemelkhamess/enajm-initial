from parametres.managers import AnneeFilteredManager
from django.db import models
from annee.models import Annee
from branches.models import Secteur
from formations.models import Formation
from django.utils.translation import gettext_lazy as _


class Etudiant(models.Model):
    objects = AnneeFilteredManager('annee')
    HOMME = 'H'
    FEMME = 'F'
    SEXE_CHOICES = [
        (HOMME, _('Homme')),
        (FEMME, _('Femme')),
    ]

    CELIBATAIRE = 'C'
    MARIE = 'M'
    DIVORCE = 'D'
    SITUATION_AMOUREUSE_CHOICES = [
        (CELIBATAIRE, _('Célibataire')),
        (MARIE, _('Marié(e)')),
        (DIVORCE, _('Divorcé(e)')),
    ]

    BREVET = 'B'
    BACCALAUREAT = 'BAC'
    LICENCE = 'L'
    MAITRISE = 'M'
    DOCTORAT = 'D'
    DIPLOME_CHOICES = [
        (BREVET, _('Brevet')),
        (BACCALAUREAT, _('Baccalauréat')),
        (LICENCE, _('Licence')),
        (MAITRISE, _('Maîtrise')),
        (DOCTORAT, _('Doctorat')),
    ]

    class Meta:
        db_table = 'etudiants'
        verbose_name = _("Étudiant")
        verbose_name_plural = _("Étudiants")

    nom = models.CharField(_("Nom"), max_length=100)
    prenom = models.CharField(_("Prénom"), max_length=100)
    matricule = models.CharField(_("Matricule"), max_length=20, unique=True)
    nni = models.CharField(_("NNI"), max_length=20, unique=True, blank=True, null=True)
    date_naissance = models.IntegerField(_("Date de naissance"), blank=True, null=True)
    lieu_naissance = models.CharField(_("Lieu de naissance"), max_length=100, blank=True, null=True)
    sexe = models.CharField(_("Sexe"), max_length=1, choices=SEXE_CHOICES, blank=True, null=True)
    telephone = models.CharField(_("Téléphone"), max_length=20, blank=True, null=True)
    email = models.EmailField(_("Email"), blank=True, null=True)
    photo = models.ImageField(_("Photo"), upload_to='photos/', blank=True, null=True)
    secteur = models.ForeignKey(Secteur, verbose_name=_("Secteur"), on_delete=models.CASCADE, related_name='etudiants',
                                default=1)
    annee = models.ForeignKey(Annee, verbose_name=_("Année"), on_delete=models.CASCADE)

    # Nouveaux champs
    situation_amoureuse = models.CharField(
        _("Situation amoureuse"),
        max_length=1,
        choices=SITUATION_AMOUREUSE_CHOICES,
        blank=True,
        null=True
    )

    diplomes = models.CharField(
        _("Diplômes"),
        max_length=100,
        blank=True,
        null=True,
        help_text=_("Diplômes obtenus (séparés par des virgules)")
    )

    nombre_enfants = models.PositiveIntegerField(
        _("Nombre d'enfants"),
        blank=True,
        null=True,
        default=0
    )

    def __str__(self):
        return f"{self.nom} {self.prenom} ({self.matricule})"

    @property
    def formation(self):
        """Propriété pour accéder à la formation via le secteur"""
        return self.secteur.formation