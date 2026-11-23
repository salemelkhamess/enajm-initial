from presenceetudiant.models import PresenceEtudiant, q_comptee
from django.db.models import Count
from parametres.utils import get_annee_courante
from parametres.models import Parametres


def critical_absences(request):
    try:
        if not Parametres.get_real_instance().alertes_absences_actives:
            return {'critical_absences': []}
    except Exception:
        pass
    critical_absences = PresenceEtudiant.objects.filter(
        q_comptee(), annee=get_annee_courante()
    ).values(
        'etudiant__nom', 'etudiant__prenom', 'matiere__nom'
    ).annotate(total=Count('id')).filter(total__gte=4)
    return {
        'critical_absences': critical_absences
    }

def niveaux_actifs(request):
    """Vrai s'il existe des « niveaux de langue » (ancienne fonction, remplacée par les groupes) : sinon on la masque."""
    try:
        from niveaux.models import Niveau
        return {'a_niveaux_actifs': Niveau.actifs().exists()}
    except Exception:
        return {'a_niveaux_actifs': False}
