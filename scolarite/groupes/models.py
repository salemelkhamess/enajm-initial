from django.db import models
from django.utils.translation import gettext_lazy as _

from annee.models import Annee
from branches.models import Secteur  # noqa: F401  (réservé : filtres par classe)
from etudiant.models import Etudiant
from formations.models import Formation
from parametres.managers import AnneeFilteredManager
from professeur.models import Professeur
from salle.models import Salle


class Groupe(models.Model):
    """
    Groupe d'élèves fonctionnaires, paramétrable : G1Ad, G2F, GAar, GBar, GA, GB…
    Un groupe appartient à une année, à un bloc (formation : Admin Pub, Finances…) et à un TYPE :
    groupe de français, groupe d'arabe, ou « section » (découpage d'une classe en sous-groupes, sans langue).
    Un élève ne peut être que dans UN groupe par type (un de français, un d'arabe, une section).
    """
    LANGUES = [('fr', _("Français")), ('ar', _("Arabe")), ('', _("Section (hors langue)"))]

    objects = AnneeFilteredManager('annee')

    annee = models.ForeignKey(Annee, on_delete=models.PROTECT, related_name='groupes', verbose_name=_("Année"))
    bloc = models.ForeignKey(Formation, on_delete=models.SET_NULL, null=True, blank=True, related_name='groupes',
                             verbose_name=_("Bloc (formation)"))
    code = models.CharField(_("Code du groupe"), max_length=30, help_text=_("Ex. : G1Ad, G2F, GAar, GBar"))
    langue = models.CharField(_("Type de groupe"), max_length=2, choices=LANGUES, blank=True, default='')
    niveau_langue = models.CharField(_("Niveau de langue"), max_length=100, blank=True, help_text=_("Ex. : A1.1, A2.2 / A2.3, ب1"))
    intitule = models.CharField(_("Intitulé"), max_length=150, blank=True, help_text=_("Ex. : Groupe 1"))
    nom_ar = models.CharField(_("Nom (arabe)"), max_length=150, blank=True,
                              help_text=_("Nom affiché en arabe à la place du code (ex. : المجموعة 4 - الفرنسية (المالية))."))
    nom_fr = models.CharField(_("Nom (français)"), max_length=150, blank=True,
                              help_text=_("Nom affiché en français (à défaut : le code)."))
    professeur = models.ForeignKey(Professeur, on_delete=models.SET_NULL, null=True, blank=True,
                                   related_name='groupes_langue', verbose_name=_("Professeur"))
    professeur_texte = models.CharField(_("Professeur (nom libre)"), max_length=150, blank=True,
                                        help_text=_("Utilisé si le professeur n'est pas dans la liste."))
    coordinateur = models.CharField(_("Coordinateur"), max_length=150, blank=True)
    salle = models.ForeignKey(Salle, on_delete=models.SET_NULL, null=True, blank=True, related_name='groupes',
                              verbose_name=_("Salle"))
    horaire = models.CharField(_("Horaire"), max_length=60, blank=True, help_text=_("Ex. : 10-12"))
    actif = models.BooleanField(_("Actif"), default=True)
    etudiants = models.ManyToManyField(Etudiant, through='Affectation', related_name='groupes', blank=True,
                                       verbose_name=_("Élèves"))

    class Meta:
        db_table = 'groupes'
        verbose_name = _("Groupe")
        verbose_name_plural = _("Groupes")
        ordering = ['bloc__nom', 'langue', 'code']
        unique_together = [('annee', 'bloc', 'code')]

    def __str__(self):
        return self.nom_affiche

    @property
    def nom_affiche(self):
        """Nom du groupe dans la langue de l'interface (à défaut : le code)."""
        from django.utils import translation
        if (translation.get_language() or '').startswith('ar'):
            return self.nom_ar or self.nom_fr or self.code
        return self.nom_fr or self.nom_ar or self.code

    @property
    def professeur_affiche(self):
        return str(self.professeur).strip() if self.professeur_id else self.professeur_texte

    @property
    def libelle(self):
        """« G1Ad — Groupe 1 (A / A1.1) »"""
        extra = " — ".join(x for x in (self.niveau_langue,) if x)
        return f"{self.nom_affiche} — {extra}" if extra else self.nom_affiche

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        # la langue du groupe est recopiée sur ses affectations (contrainte : un groupe par langue et par élève)
        self.affectations.exclude(langue=self.langue).update(langue=self.langue)


class Affectation(models.Model):
    """Appartenance d'un élève à un groupe. `niveau_eleve` : niveau individuel (ex. أ1) lorsque la liste le précise."""
    groupe = models.ForeignKey(Groupe, on_delete=models.CASCADE, related_name='affectations')
    etudiant = models.ForeignKey(Etudiant, on_delete=models.CASCADE, related_name='affectations')
    langue = models.CharField(max_length=2, editable=False, blank=True, default='')
    niveau_eleve = models.CharField(_("Niveau de l'élève"), max_length=20, blank=True)

    class Meta:
        db_table = 'groupes_affectations'
        unique_together = [('etudiant', 'langue')]

    def save(self, *args, **kwargs):
        self.langue = self.groupe.langue
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.etudiant} → {self.groupe}"
