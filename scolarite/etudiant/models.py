from parametres.managers import AnneeFilteredManager
from django.db import models
from annee.models import Annee
from branches.models import Secteur
from formations.models import Formation
from django.utils import translation
from django.utils.translation import gettext_lazy as _


def ordre_matricule_croissant():
    """Tri « du plus petit au plus grand » sur le matricule (numéros de même longueur comparés comme des nombres)."""
    from django.db.models.functions import Length
    return [Length('matricule').asc(), 'matricule']


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
    DEUG = 'DEUG'
    MASTER = 'MASTER'
    MAITRISE = 'M'
    DOCTORAT = 'D'
    # (code, arabe, français) dans l'ordre d'affichage. Le code 'M' (Maîtrise) est conservé pour les données existantes.
    DIPLOMES = [
        (BREVET, 'شهادة ختم الدروس الإعدادية', 'Brevet'),
        (BACCALAUREAT, 'البكالوريا', 'Baccalauréat'),
        (LICENCE, 'الليسانس', 'Licence'),
        (DEUG, 'شهادة الدراسات الجامعية', 'DEUG'),
        (MASTER, 'الماستر', 'Master'),
        (MAITRISE, 'الإجازة', 'Maîtrise'),
        (DOCTORAT, 'الدكتوراه', 'Doctorat'),
    ]
    DIPLOME_CHOICES = [(code, f"{ar}: {fr}") for code, ar, fr in DIPLOMES]

    @staticmethod
    def diplomes_liste(valeur):
        """Liste de codes de diplômes à partir de la valeur stockée : liste, texte « ['L', 'M'] » ou « L, M »."""
        import ast
        if not valeur:
            return []
        if isinstance(valeur, (list, tuple, set)):
            return [str(v).strip() for v in valeur if str(v).strip()]
        texte = str(valeur).strip()
        try:
            lu = ast.literal_eval(texte)
            if isinstance(lu, (list, tuple, set)):
                return [str(v).strip() for v in lu if str(v).strip()]
            texte = str(lu)
        except (ValueError, SyntaxError):
            pass
        return [p.strip(" '\"[]") for p in texte.split(',') if p.strip(" '\"[]")]

    class Meta:
        db_table = 'etudiants'
        verbose_name = _("Étudiant")
        verbose_name_plural = _("Étudiants")

    nom = models.CharField(_("Nom (arabe)"), max_length=100)
    prenom = models.CharField(_("Prénom (arabe)"), max_length=100)
    nom_fr = models.CharField(_("Nom (français)"), max_length=100, blank=True, null=True)
    prenom_fr = models.CharField(_("Prénom (français)"), max_length=100, blank=True, null=True)
    matricule = models.CharField(_("Matricule"), max_length=20, unique=True)
    nni = models.CharField(_("NNI"), max_length=20, unique=True, blank=True, null=True)
    date_naissance = models.IntegerField(_("Date de naissance"), blank=True, null=True)
    lieu_naissance = models.CharField(_("Lieu de naissance (arabe)"), max_length=100, blank=True, null=True)
    lieu_naissance_fr = models.CharField(_("Lieu de naissance (français)"), max_length=100, blank=True, null=True)
    sexe = models.CharField(_("Sexe"), max_length=1, choices=SEXE_CHOICES, blank=True, null=True)
    telephone = models.CharField(_("Téléphone"), max_length=20, blank=True, null=True)
    email = models.EmailField(_("Email"), blank=True, null=True)
    photo = models.ImageField(_("Photo"), upload_to='photos/', blank=True, null=True)
    secteur = models.ForeignKey(Secteur, verbose_name=_("Secteur"), on_delete=models.CASCADE, related_name='etudiants',
                                default=1)
    annee = models.ForeignKey(Annee, verbose_name=_("Année"), on_delete=models.CASCADE)
    # Niveau (facultatif, paramétrable) : sert à regrouper des élèves de secteurs différents
    niveau = models.ForeignKey('niveaux.Niveau', verbose_name=_("Niveau"), null=True, blank=True,
                               on_delete=models.PROTECT, related_name='etudiants')

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
        return f"{self.nom_prenom} ({self.matricule})"

    # --- affichage selon la langue active (arabe / français, avec repli sur l'autre langue) ---
    @staticmethod
    def _langue_arabe():
        return (translation.get_language() or '').startswith('ar')

    def _paire_langue(self):
        """(nom, prénom) de la langue active ; si le nom manque dans cette langue, la paire de l'autre langue."""
        arabe = (self.nom or '', self.prenom or '')
        francais = (self.nom_fr or '', self.prenom_fr or '')
        prefere, autre = (arabe, francais) if self._langue_arabe() else (francais, arabe)
        return prefere if prefere[0] else autre

    @property
    def nom_langue(self):
        return self._paire_langue()[0]

    @property
    def prenom_langue(self):
        return self._paire_langue()[1]

    @property
    def nom_prenom(self):
        """Nom complet en arabe, NOM DE LA PERSONNE EN PREMIER (champ « prénom »), puis nom du père (champ « nom »),
        sans doublon si l'un contient déjà l'autre."""
        from .noms import fusionner_noms
        return fusionner_noms(self.prenom, self.nom)

    @property
    def nom_prenom_fr(self):
        """Nom complet en français : nom de la personne (champ « nom ») puis nom du père (champ « prénom »)."""
        from .noms import fusionner_noms
        return fusionner_noms(self.nom_fr, self.prenom_fr)

    @property
    def nom_complet_ar(self):
        """Nom complet en arabe : prénom puis nom, sans doublon."""
        from .noms import fusionner_noms
        return fusionner_noms(self.prenom, self.nom)

    @property
    def nom_complet_fr(self):
        """Nom complet en français : nom puis prénom, sans doublon (vide si non renseigné)."""
        return self.nom_prenom_fr

    @property
    def nom_complet_langue(self):
        """Nom complet dans la langue active, sans doublon (à défaut de nom dans cette langue : l'autre langue)."""
        from .noms import fusionner_noms
        nom, prenom = self._paire_langue()
        return fusionner_noms(prenom, nom) if self._langue_arabe() else fusionner_noms(nom, prenom)

    @property
    def lieu_naissance_langue(self):
        if self._langue_arabe():
            return self.lieu_naissance or self.lieu_naissance_fr or ''
        return self.lieu_naissance_fr or self.lieu_naissance or ''

    @property
    def types_documents(self):
        """[(libellé du type, nombre)] des documents déjà enregistrés (utiliser prefetch_related('documents'))."""
        comptes = {}
        for d in self.documents.all():
            libelle = str(d.get_type_document_display())
            comptes[libelle] = comptes.get(libelle, 0) + 1
        return list(comptes.items())

    @property
    def formation(self):
        """Propriété pour accéder à la formation via le secteur"""
        return self.secteur.formation