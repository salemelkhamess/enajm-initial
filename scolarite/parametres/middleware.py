# parametres/middleware.py
import threading

_state = threading.local()
SESSION_KEY = 'annee_consultee_id'


def get_annee_consultee_id():
    """Id de l'année choisie par l'utilisateur pour consulter les données (ou None)."""
    return getattr(_state, 'annee_id', None)


def cached_real_instance(loader):
    """Instance des paramètres, chargée une seule fois par requête (hors requête : toujours rechargée)."""
    if getattr(_state, 'in_request', False):
        obj = getattr(_state, 'params', None)
        if obj is None:
            obj = _state.params = loader()
        return obj
    return loader()


def cached_periode(annee_id, loader):
    """(année, premier trimestre) de l'année consultée, chargés une fois par requête."""
    if not getattr(_state, 'in_request', False):
        return loader()
    cache = getattr(_state, 'periodes', None)
    if cache is None:
        cache = _state.periodes = {}
    if annee_id not in cache:
        cache[annee_id] = loader()
    return cache[annee_id]


def invalider_cache_parametres():
    _state.params = None
    _state.periodes = None
    if hasattr(_state, 'real_id'):
        del _state.real_id


def annee_effective_id():
    """Id de l'année dont on affiche les données : année consultée, sinon année active."""
    consultee = get_annee_consultee_id()
    if consultee:
        return consultee
    # Pas de cache hors requête (shell, commandes) : la valeur pourrait être périmée.
    if getattr(_state, 'in_request', False) and hasattr(_state, 'real_id'):
        return _state.real_id
    from .models import Parametres
    real_id = Parametres.objects.values_list('annee_courante_id', flat=True).first()
    if getattr(_state, 'in_request', False):
        _state.real_id = real_id
    return real_id


class AnneeConsulteeMiddleware:
    """Rend l'année choisie dans la session accessible à Parametres.get_instance()."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        session = getattr(request, 'session', None)
        _state.annee_id = session.get(SESSION_KEY) if session is not None else None
        _state.in_request = True
        invalider_cache_parametres()
        try:
            return self.get_response(request)
        finally:
            _state.annee_id = None
            _state.in_request = False


def _invalider_a_la_sauvegarde(sender, **kwargs):
    invalider_cache_parametres()
