from datetime import date, timedelta

from emploie.models import EmploiDuTemps
from professeur.models import Professeur

JOURS = ['Lundi', 'Mardi', 'Mercredi', 'Jeudi', 'Vendredi', 'Samedi', 'Dimanche']

ROLES_GESTION = ('ADMIN', 'SUPER_ADMIN', 'MANAGER', 'POINTEUR', 'DOCTOR')


def get_professeur(user):
    """Fiche professeur liée au compte (lien explicite, sinon même adresse email)."""
    if not user.is_authenticated:
        return None
    prof = Professeur.objects.filter(user=user).first()
    if prof is None and user.email:
        prof = Professeur.objects.filter(email__iexact=user.email, user__isnull=True).first()
    return prof


def est_professeur_seul(user):
    """Compte avec le rôle Professeur et aucun rôle de gestion : accès limité à l'espace professeur."""
    return (user.is_authenticated and user.has_role('PROFESSEUR')
            and not any(user.has_role(r) for r in ROLES_GESTION))


def creneaux(prof, trimestre=None):
    """Créneaux d'emploi du temps du professeur (année affichée), éventuellement d'un seul trimestre."""
    qs = (EmploiDuTemps.objects.filter(professeur=prof)
          .select_related('matiere', 'secteur', 'salle', 'trimestre', 'annee'))
    if trimestre is not None:
        qs = qs.filter(trimestre=trimestre)
    ordre = {j: i for i, j in enumerate(JOURS)}
    return sorted(qs, key=lambda c: (ordre.get(c.jour, 9), c.heure_debut))


def couples_matiere_secteur(prof):
    """{(matiere_id, secteur_id)} enseignés par le professeur dans l'année affichée."""
    return set(EmploiDuTemps.objects.filter(professeur=prof).values_list('matiere_id', 'secteur_id').distinct())


def dernier_jour(jour_nom, aujourdhui=None):
    """Dernière date (aujourd'hui incluse) qui tombe un « jour_nom » (ex. 'Lundi')."""
    aujourdhui = aujourdhui or date.today()
    if jour_nom not in JOURS:
        return aujourdhui
    ecart = (aujourdhui.weekday() - JOURS.index(jour_nom)) % 7
    return aujourdhui - timedelta(days=ecart)


def jour_de(d):
    return JOURS[d.weekday()]
