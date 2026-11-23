"""Pages d'erreur conviviales (403, 404, 500, 400, session expirée), dans la langue de l'utilisateur."""
import logging

from django.conf import settings
from django.core.exceptions import PermissionDenied
from django.http import Http404, HttpResponse
from django.template.loader import render_to_string
from django.utils.translation import gettext as _

logger = logging.getLogger(__name__)


def _page(request, status, titre, message):
    contexte = {'code': status, 'titre': titre, 'message': message}
    try:
        html = render_to_string('errors/erreur.html', contexte, request=request)
    except Exception:  # la page d'erreur elle-même ne doit jamais échouer
        html = f"<h1>{status}</h1><p>{titre}</p>"
    return HttpResponse(html, status=status)


def erreur_400(request, exception=None):
    return _page(request, 400, _("Requête invalide"), _("La demande envoyée n'est pas valide. Retournez à la page précédente et réessayez."))


def erreur_403(request, exception=None):
    return _page(request, 403, _("Accès refusé"), _("Vous n'avez pas l'autorisation d'accéder à cette page."))


def erreur_404(request, exception=None):
    return _page(request, 404, _("Page introuvable"), _("La page demandée n'existe pas ou a été déplacée."))


def erreur_500(request):
    return _page(request, 500, _("Une erreur est survenue"),
                 _("Un problème technique est survenu. Veuillez réessayer. Si le problème persiste, contactez l'administration."))


def csrf_failure(request, reason=""):
    return _page(request, 403, _("Session expirée"),
                 _("Votre session a expiré ou le formulaire n'est plus valide. Rechargez la page puis réessayez."))


class ErreursConvivialesMiddleware:
    """
    Remplace les pages techniques de Django (erreurs 500, 404) par des pages claires, même en mode DEBUG.
    Désactivable pour le développement avec la variable d'environnement ERREURS_TECHNIQUES=1.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        if (getattr(settings, 'ERREURS_CONVIVIALES', True) and response.status_code == 404
                and b'Using the URLconf defined in' in response.content[:4000]):
            return erreur_404(request)
        return response

    def process_exception(self, request, exception):
        if not getattr(settings, 'ERREURS_CONVIVIALES', True) or isinstance(exception, (Http404, PermissionDenied)):
            return None
        logger.exception("Erreur inattendue sur %s", request.path)
        return erreur_500(request)
