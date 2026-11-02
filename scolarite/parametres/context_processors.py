# parametres/context_processors.py
from annee.models import Annee
from .models import Parametres


def parametres_context(request):
    try:
        parametres = Parametres.get_instance()
        reel = Parametres.get_real_instance()
        return {
            'annee_courante': parametres.annee_courante,
            'trimestre_courant': parametres.trimestre_courant,
            'annee_active_id': reel.annee_courante_id,
            'annees_disponibles': Annee.objects.order_by('-numero_annee'),
            'annee_consultee_differente': parametres.annee_courante_id != reel.annee_courante_id,
            'professeur_seul': getattr(request, 'professeur_seul', False),
        }
    except Exception:
        return {}
