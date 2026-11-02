from functools import wraps

from django.shortcuts import render

from .utils import get_professeur


def professeur_required(view):
    """Réservé aux comptes ayant le rôle Professeur (ou un rôle de gestion) ET une fiche professeur liée."""
    @wraps(view)
    def wrapper(request, *args, **kwargs):
        user = request.user
        prof = get_professeur(user)
        if prof is None or not (user.has_role('PROFESSEUR') or user.is_superuser or user.has_role('ADMIN')
                                or user.has_role('SUPER_ADMIN')):
            return render(request, 'espace_prof/sans_fiche.html', status=403)
        request.professeur = prof
        return view(request, *args, **kwargs)
    return wrapper
