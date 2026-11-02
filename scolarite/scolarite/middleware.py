from django.shortcuts import redirect
from django.conf import settings
import re
from django.utils import translation

# Adresses accessibles sans être connecté (le préfixe de langue /fr ou /ar est facultatif)
PUBLIC_PATHS = [
    r'^/(?:(?:fr|ar)/?)?$',                   # page de connexion
    r'^/(?:fr|ar)/language/',                 # changement de langue
    r'^/(?:(?:fr|ar)/)?i18n/',                # setlang de Django (avec ou sans préfixe de langue)
    r'^/static/',
    r'^/media/',
    r'^/favicon\.ico$',
    r'^/(?:(?:fr|ar)/)?admin/',               # l'admin Django gère sa propre authentification
    r'^/(?:(?:fr|ar)/)?api/',                 # API REST (permissions propres, voir settings)
]
PUBLIC_RE = [re.compile(p) for p in PUBLIC_PATHS]

# Pages accessibles à un compte « Professeur » sans rôle de gestion
PROFESSEUR_PATHS = [
    r'^/(?:fr|ar)/espace-prof/',
    r'^/(?:fr|ar)/users/profile/$',
    r'^/(?:fr|ar)/logout/$',
]
PROFESSEUR_RE = [re.compile(p) for p in PROFESSEUR_PATHS]


class LoginRequiredMiddleware:
    """Redirige vers la page de connexion tout visiteur non connecté (hors pages publiques)."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if not request.user.is_authenticated and not any(r.match(request.path) for r in PUBLIC_RE):
            langue = getattr(request, 'LANGUAGE_CODE', None) or settings.LANGUAGE_CODE
            return redirect(f"/{langue}/?next={request.path}")
        return self.get_response(request)


class ProfesseurScopeMiddleware:
    """
    Un compte ayant le rôle Professeur et aucun rôle de gestion n'accède qu'à son espace professeur,
    toujours sur l'année active (pas de sélecteur d'année).
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        from espace_prof.utils import est_professeur_seul
        user = request.user
        if user.is_authenticated and est_professeur_seul(user):
            from parametres import middleware as annee_mw
            annee_mw._state.annee_id = None
            request.professeur_seul = True
            if not any(r.match(request.path) for r in PROFESSEUR_RE + PUBLIC_RE):
                langue = getattr(request, 'LANGUAGE_CODE', None) or settings.LANGUAGE_CODE
                return redirect(f"/{langue}/espace-prof/")
        return self.get_response(request)


class ForceLangMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if 'lang' in request.GET:
            user_language = request.GET['lang']
            translation.activate(user_language)
            request.LANGUAGE_CODE = translation.get_language()

        response = self.get_response(request)
        return response
