from parametres.managers import AnneeFilteredManager
from django.db import models
from annee.models import Annee
from branches.models import Secteur
from etudiant.models import Etudiant
from matiers.models import Matiere
from trimestre.models import Trimestre
from datetime import date, timedelta
from django.utils import timezone
from django.db.models import Count, F, Q

from django.db.models.functions import ExtractWeek, ExtractMonth, ExtractYear
import os
import uuid
from django.conf import settings
from django.core.files.storage import FileSystemStorage

# Documents de justification (certificats médicaux…) : hors du dossier public /media/
stockage_prive = FileSystemStorage(location=settings.PRIVATE_MEDIA_ROOT)


def chemin_justification(instance, nom_fichier):
    nom = os.path.basename(nom_fichier).replace(' ', '_')
    dossier = f"periode-{instance.periode_id}" if instance.periode_id else str(instance.absence_id)
    return f"justifications/{dossier}/{uuid.uuid4().hex[:8]}_{nom}"

# Une absence enregistrée reste « en attente » pendant ce délai (justification possible).
# Passé ce délai sans justification, elle est validée et compte comme absence.
DELAI_VALIDATION_ABSENCE = timedelta(hours=72)


def seuil_validation():
    """Les absences enregistrées avant cet instant sont validées (si non justifiées)."""
    return timezone.now() - DELAI_VALIDATION_ABSENCE


def q_soumise():
    """Justification déposée par le médecin, en attente de la décision de l'administration."""
    return Q(present=False, is_justified=False, justif_etat='soumise')


def q_en_attente():
    """
    Absence non justifiée qui n'est pas encore une absence : enregistrée depuis moins de 72 h,
    ou justification soumise en attente de décision (le délai de 72 h est alors suspendu).
    """
    return Q(present=False, is_justified=False) & (
        Q(justif_etat='soumise') | Q(date_enregistrement__gt=seuil_validation()))


def q_comptee():
    """Absence validée : non justifiée, sans justification en cours, délai de 72 h écoulé (ou ancienne)."""
    return Q(present=False, is_justified=False) & ~Q(justif_etat='soumise') & (
        Q(date_enregistrement__isnull=True) | Q(date_enregistrement__lte=seuil_validation()))


class PresenceEtudiant(models.Model):
    objects = AnneeFilteredManager('annee')
    JOURS_CHOIX = [
        ('Lundi', 'Lundi'),
        ('Mardi', 'Mardi'),
        ('Mercredi', 'Mercredi'),
        ('Jeudi', 'Jeudi'),
        ('Vendredi', 'Vendredi'),
        ('Samedi', 'Samedi'),
    ]

    etudiant = models.ForeignKey(Etudiant, on_delete=models.CASCADE)
    matiere = models.ForeignKey(Matiere, on_delete=models.CASCADE, default=1)
    present = models.BooleanField(default=True)
    justification = models.TextField(blank=True, null=True)
    date_justification = models.DateField(blank=True, null=True)
    annee = models.ForeignKey(Annee, on_delete=models.CASCADE, default=1)
    trimestre = models.ForeignKey(Trimestre, on_delete=models.CASCADE, default=1)
    jour = models.CharField(max_length=10, choices=JOURS_CHOIX ,blank=True, null=True)  # Nouveau champ
    date_cours = models.DateField(blank=True, null=True)  # Nouveau champ pour la date du cours
    status  = models.BooleanField(default=False)
    is_justified  = models.BooleanField(default=False)
    date_enregistrement = models.DateTimeField(null=True, blank=True, editable=False)

    # Justification : déposée par le médecin, décidée par l'administration / le pointeur / le super administrateur
    JUSTIF_ETATS = [
        ('aucune', 'Aucune'),
        ('soumise', 'Soumise (en attente de validation)'),
        ('acceptee', 'Acceptée'),
        ('refusee', 'Refusée'),
    ]
    justif_etat = models.CharField(max_length=10, choices=JUSTIF_ETATS, default='aucune')
    justif_soumise_par = models.ForeignKey('users.User', null=True, blank=True, on_delete=models.SET_NULL,
                                           related_name='+', editable=False)
    justif_soumise_le = models.DateTimeField(null=True, blank=True, editable=False)
    justif_decidee_par = models.ForeignKey('users.User', null=True, blank=True, on_delete=models.SET_NULL,
                                           related_name='+', editable=False)
    justif_decidee_le = models.DateTimeField(null=True, blank=True, editable=False)
    justif_motif_refus = models.TextField(blank=True, null=True)
    # Justification par période (autorisation de plusieurs jours) à laquelle cette absence est rattachée
    justif_periode = models.ForeignKey('JustificationPeriode', null=True, blank=True, on_delete=models.SET_NULL,
                                       related_name='absences', editable=False)

    class Meta:
        db_table = 'presence_etudiant'
        unique_together = ['etudiant', 'matiere', 'date_cours', 'jour']  # Modification

    def __str__(self):
        return f"{self.etudiant} - {self.matiere} - {self.date_cours} - {self.jour}"

    def save(self, *args, **kwargs):
        # L'horloge des 72 h démarre quand l'absence est enregistrée (ou quand une présence devient absence).
        if self.present:
            self.date_enregistrement = None
        elif self.date_enregistrement is None:
            ancien = None
            if self.pk:
                ancien = PresenceEtudiant._base_manager.filter(pk=self.pk).values('present', 'date_enregistrement').first()
            if ancien is None or ancien['present']:
                self.date_enregistrement = timezone.now()
            else:
                self.date_enregistrement = ancien['date_enregistrement']  # absence déjà validée : on la garde telle quelle
        self._rattacher_a_une_periode()
        super().save(*args, **kwargs)

    def _rattacher_a_une_periode(self):
        """
        Une absence enregistrée pendant une période déjà justifiée (autorisation de plusieurs jours) reprend
        cette justification : en attente de validation, ou directement justifiée si la période est acceptée.
        Les absences déjà validées (72 h écoulées) ne sont plus justifiables.
        """
        if (self.present or self.is_justified or self.justif_periode_id or self.justif_etat != 'aucune'
                or not self.date_cours or not self.etudiant_id):
            return
        if not (self.date_enregistrement and self.date_enregistrement > seuil_validation()):
            return
        periode = JustificationPeriode._base_manager.filter(
            etudiant_id=self.etudiant_id, etat__in=('soumise', 'acceptee'),
            date_debut__lte=self.date_cours, date_fin__gte=self.date_cours).order_by('-soumise_le').first()
        if periode is None:
            return
        self.justif_periode = periode
        self.justification = periode.justification
        self.date_justification = periode.soumise_le.date() if periode.soumise_le else None
        self.justif_soumise_par = periode.soumise_par
        self.justif_soumise_le = periode.soumise_le
        if periode.etat == 'acceptee':
            self.is_justified, self.status, self.justif_etat = True, True, 'acceptee'
            self.justif_decidee_par, self.justif_decidee_le = periode.decidee_par, periode.decidee_le
        else:
            self.justif_etat = 'soumise'

    # --- états d'une absence ---------------------------------------------------------------
    @property
    def etat_absence(self):
        """'present', 'justifiee', 'justification_soumise', 'en_attente' ou 'validee'."""
        if self.present:
            return 'present'
        if self.is_justified:
            return 'justifiee'
        if self.justif_etat == 'soumise':
            return 'justification_soumise'
        if self.date_enregistrement and self.date_enregistrement > seuil_validation():
            return 'en_attente'
        return 'validee'

    @property
    def heures_avant_validation(self):
        """Heures restantes avant validation (0 si déjà validée ou justifiée)."""
        if self.etat_absence != 'en_attente':
            return 0
        reste = self.date_enregistrement + DELAI_VALIDATION_ABSENCE - timezone.now()
        return max(int(reste.total_seconds() // 3600) + 1, 1)

    @property
    def justifiable(self):
        """Le médecin peut justifier tant que l'absence n'est pas validée (ni déjà justifiée)."""
        return self.etat_absence in ('en_attente', 'justification_soumise')

    def valider_maintenant(self):
        """Valide l'absence sans attendre la fin du délai."""
        self.date_enregistrement = timezone.now() - DELAI_VALIDATION_ABSENCE
        self.save(update_fields=['date_enregistrement'])

    @classmethod
    def comptees(cls):
        """Absences validées (celles qui comptent) de l'année affichée."""
        return cls._actifs().filter(q_comptee())

    @classmethod
    def en_attente(cls):
        """Absences en attente de justification (72 h) de l'année affichée."""
        return cls._actifs().filter(q_en_attente())


    @classmethod
    def _annee_active(cls):
        from parametres.utils import get_annee_courante
        return get_annee_courante()

    @classmethod
    def _actifs(cls):
        """Présences de l'année active uniquement"""
        return cls.objects.filter(annee=cls._annee_active())

    @classmethod
    def get_presences_for_secteur(cls, secteur_id, date_cours, trimestre_id, jour):
        return cls._actifs().filter(
            etudiant__secteur_id=secteur_id,
            date_cours=date_cours,
            trimestre_id=trimestre_id,
            jour=jour
        )

    @classmethod
    def get_students_with_hours_of_absence(cls, hours):
        """
        Récupère les étudiants ayant exactement le nombre d'heures d'absence spécifié.
        Une séance = 2h d'absence.

        Args:
            hours (int): Nombre total d'heures d'absence recherché

        Returns:
            QuerySet: Étudiants avec leur nombre d'heures d'absence exact
        """
        # Convertir les heures en nombre de séances (1 séance = 2h)
        sessions_count = hours // 2

        # Récupérer les étudiants avec exactement ce nombre de séances d'absence
        result = cls.comptees().values(
            'etudiant_id',
            'etudiant__nom',
            'etudiant__prenom'
        ).annotate(
            total_absences=Count('id'),
            total_hours=F('total_absences') * 2
        ).filter(
            total_hours=hours
        ).order_by('etudiant__nom', 'etudiant__prenom')

        return result

    @classmethod
    def get_students_with_min_hours_of_absence(cls, hours):
        """
        Récupère les étudiants ayant au moins le nombre d'heures d'absence spécifié.
        Une séance = 2h d'absence.

        Args:
            hours (int): Nombre minimum d'heures d'absence

        Returns:
            QuerySet: Étudiants avec leur nombre d'heures d'absence
        """
        # Calculer le nombre minimum de séances
        min_sessions = hours // 2

        result = cls.comptees().values(
            'etudiant_id',
            'etudiant__nom',
            'etudiant__prenom'
        ).annotate(
            total_absences=Count('id'),
            total_hours=F('total_absences') * 2
        ).filter(
            total_hours__gte=hours
        ).order_by('etudiant__nom', 'etudiant__prenom')

        return result

    @classmethod
    def get_global_absence_stats(cls):
        """
        Récupère les statistiques globales d'absences pour:
        - Aujourd'hui
        - Cette semaine
        - Ce mois

        Returns:
            dict: Dictionnaire contenant les totaux d'absences
        """
        from datetime import date, timedelta
        today = date.today()
        start_of_week = today - timedelta(days=today.weekday())
        start_of_month = date(today.year, today.month, 1)

        # Filtre des absences non justifiées
        base_queryset = cls.comptees()

        # Absences aujourd'hui
        absences_aujourdhui = base_queryset.filter(
            date_cours=today
        ).count()

        # Absences cette semaine
        absences_cette_semaine = base_queryset.filter(
            date_cours__gte=start_of_week,
            date_cours__lte=today
        ).count()

        # Absences ce mois
        absences_ce_mois = base_queryset.filter(
            date_cours__gte=start_of_month,
            date_cours__lte=today
        ).count()

        return {
            'aujourdhui': absences_aujourdhui,
            'cette_semaine': absences_cette_semaine,
            'ce_mois': absences_ce_mois,
        }

    @classmethod
    def get_top_absent_students(cls, period='day', limit=10):
        """
        Récupère les étudiants les plus absents selon la période spécifiée
        Args:
            period: 'day' (aujourd'hui), 'week' (cette semaine), 'month' (ce mois)
            limit: nombre maximum d'étudiants à retourner
        """
        today = date.today()

        if period == 'day':
            date_filter = Q(date_cours=today)
        elif period == 'week':
            start_of_week = today - timedelta(days=today.weekday())
            date_filter = Q(date_cours__gte=start_of_week, date_cours__lte=today)
        elif period == 'month':
            start_of_month = date(today.year, today.month, 1)
            date_filter = Q(date_cours__gte=start_of_month, date_cours__lte=today)
        else:
            date_filter = Q()  # Toutes les dates si période non reconnue

        top_absent = cls._actifs().filter(
            date_filter &
            q_comptee()
        ).values(
            'etudiant__id',
            'etudiant__nom',
            'etudiant__prenom',
            'etudiant__secteur__nom'
        ).annotate(
            absences=Count('id'),
            hours=F('absences') * 2  # 1 séance = 2h
        ).order_by('-absences')[:limit]

        return top_absent

    @classmethod
    def get_presence_rate_by_sector(cls, period='day'):
        """
        Calcule le taux de présence par secteur selon la période spécifiée
        Args:
            period: 'day' (aujourd'hui), 'week' (cette semaine), 'month' (ce mois)
        """
        today = date.today()

        if period == 'day':
            date_filter = Q(date_cours=today)
        elif period == 'week':
            start_of_week = today - timedelta(days=today.weekday())
            date_filter = Q(date_cours__gte=start_of_week, date_cours__lte=today)
        elif period == 'month':
            start_of_month = date(today.year, today.month, 1)
            date_filter = Q(date_cours__gte=start_of_month, date_cours__lte=today)
        else:
            date_filter = Q()  # Toutes les dates si période non reconnue

        # Total des séances par secteur pour la période
        total_seances = cls._actifs().exclude(q_en_attente()).filter(
            date_filter
        ).values(
            'etudiant__secteur__id',
            'etudiant__secteur__nom'
        ).annotate(
            total=Count('id')
        )

        # Présences par secteur pour la période
        presences = cls._actifs().filter(
            date_filter &
            Q(present=True)
        ).values(
            'etudiant__secteur__id',
            'etudiant__secteur__nom'
        ).annotate(
            present=Count('id')
        )

        # Absences non justifiées par secteur pour la période
        absences = cls._actifs().filter(
            date_filter &
            q_comptee()
        ).values(
            'etudiant__secteur__id',
            'etudiant__secteur__nom'
        ).annotate(
            absent=Count('id')
        )

        # Construction des stats par secteur
        sector_stats = []
        for sector in Secteur.objects.all():
            total = next((t for t in total_seances
                          if t['etudiant__secteur__id'] == sector.id), {'total': 0})
            present = next((p for p in presences
                            if p['etudiant__secteur__id'] == sector.id), {'present': 0})
            absent = next((a for a in absences
                           if a['etudiant__secteur__id'] == sector.id), {'absent': 0})

            taux_presence = round((present['present'] / total['total'] * 100), 2) if total['total'] > 0 else 0

            sector_stats.append({
                'secteur_id': sector.id,
                'secteur_nom': sector.nom,
                'total': total['total'],
                'present': present['present'],
                'absent': absent['absent'],
                'taux_presence': taux_presence
            })

        return sector_stats

    @classmethod
    def count_etudiants_presents(cls, period='day'):
        """
        Compte le nombre d'étudiants présents (non absents) pour une période donnée
        """
        today = date.today()
        total_etudiants = Etudiant.objects.filter(annee=cls._annee_active()).count()

        if period == 'day':
            absences = cls._actifs().filter(
                q_comptee(),
                date_cours=today
            ).values('etudiant').distinct().count()
        elif period == 'week':
            start = today - timedelta(days=today.weekday())
            absences = cls._actifs().filter(
                q_comptee(),
                date_cours__range=[start, today]
            ).values('etudiant').distinct().count()
        elif period == 'month':
            start = date(today.year, today.month, 1)
            absences = cls._actifs().filter(
                q_comptee(),
                date_cours__range=[start, today]
            ).values('etudiant').distinct().count()

        return total_etudiants - absences

    @classmethod
    def get_etudiants_presents_stats(cls):
        """Retourne les stats de présence par période"""
        return {
            'jour': cls.count_etudiants_presents(period='day'),
            'semaine': cls.count_etudiants_presents(period='week'),
            'mois': cls.count_etudiants_presents(period='month'),
            'total': Etudiant.objects.filter(annee=cls._annee_active()).count()
        }

    @classmethod
    def get_absences_justifiees_stats(cls):
        """Retourne les stats d'absences justifiées par période"""
        today = date.today()
        start_week = today - timedelta(days=today.weekday())
        start_month = date(today.year, today.month, 1)

        return {
            'jour': cls._actifs().filter(
                date_cours=today,
                present=False,
                is_justified=True,
                status=True
            ).count(),
            'semaine': cls._actifs().filter(
                date_cours__gte=start_week,
                date_cours__lte=today,
                present=False,
                is_justified=True,
                status=True
            ).count(),
            'mois': cls._actifs().filter(
                date_cours__gte=start_month,
                date_cours__lte=today,
                present=False,
                is_justified=True,
                status=True
            ).count()
        }

    @classmethod
    def get_etudiants_absents_justifies(cls, period='day'):
        """Compte les étudiants distincts absents justifiés"""
        today = date.today()

        if period == 'day':
            date_filter = Q(date_cours=today)
        elif period == 'week':
            date_filter = Q(date_cours__gte=today - timedelta(days=today.weekday()),
                            date_cours__lte=today)
        elif period == 'month':
            date_filter = Q(date_cours__gte=date(today.year, today.month, 1),
                            date_cours__lte=today)

        return cls._actifs().filter(
            date_filter &
            Q(present=False, is_justified=True, status=True)
        ).values('etudiant').distinct().count()



class DocumentJustification(models.Model):
    """Pièce jointe (certificat médical, etc.) déposée à l'appui de la justification d'une absence."""
    absence = models.ForeignKey(PresenceEtudiant, null=True, blank=True, on_delete=models.CASCADE, related_name='documents')
    periode = models.ForeignKey('JustificationPeriode', null=True, blank=True, on_delete=models.CASCADE, related_name='documents')
    fichier = models.FileField(upload_to=chemin_justification, storage=stockage_prive)
    nom = models.CharField(max_length=255)
    ajoute_par = models.ForeignKey('users.User', null=True, blank=True, on_delete=models.SET_NULL, related_name='+')
    ajoute_le = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'presence_etudiant_document'
        ordering = ['ajoute_le']

    def __str__(self):
        return self.nom



class JustificationPeriode(models.Model):
    """
    Justification d'un élève pour une période (ex. autorisation de 3 jours du 11/11 au 13/11) : toutes ses absences
    pendant cette période sont justifiées par un même dossier (texte + documents), puis validées en une fois
    par l'administration, le pointeur ou le super administrateur.
    """
    objects = AnneeFilteredManager('etudiant__annee')
    ETATS = [('soumise', 'Soumise (en attente de validation)'), ('acceptee', 'Acceptée'), ('refusee', 'Refusée')]

    etudiant = models.ForeignKey(Etudiant, on_delete=models.CASCADE, related_name='justifications_periode')
    date_debut = models.DateField()
    date_fin = models.DateField()
    justification = models.TextField()
    etat = models.CharField(max_length=10, choices=ETATS, default='soumise')
    soumise_par = models.ForeignKey('users.User', null=True, blank=True, on_delete=models.SET_NULL, related_name='+')
    soumise_le = models.DateTimeField(default=timezone.now)
    decidee_par = models.ForeignKey('users.User', null=True, blank=True, on_delete=models.SET_NULL, related_name='+')
    decidee_le = models.DateTimeField(null=True, blank=True)
    motif_refus = models.TextField(blank=True, null=True)

    class Meta:
        db_table = 'justification_periode'
        ordering = ['-date_debut', '-id']

    def __str__(self):
        return f"{self.etudiant} : {self.date_debut} → {self.date_fin}"

    @property
    def nb_jours(self):
        return (self.date_fin - self.date_debut).days + 1
