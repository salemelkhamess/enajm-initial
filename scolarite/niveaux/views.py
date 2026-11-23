from functools import wraps

from django.contrib import messages
from django.http import HttpResponseForbidden
from django.core.exceptions import PermissionDenied
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.translation import gettext as _
from django.views.decorators.http import require_POST

from .forms import NiveauForm
from .models import Niveau


def gestionnaire_requis(view):
    """Réservé à l'administrateur et au super administrateur."""
    @wraps(view)
    def wrapper(request, *args, **kwargs):
        u = request.user
        if not (u.is_authenticated and (u.is_superuser or u.has_role('ADMIN') or u.has_role('SUPER_ADMIN'))):
            raise PermissionDenied
        return view(request, *args, **kwargs)
    return wrapper


@gestionnaire_requis
def niveau_liste(request):
    """Par défaut, seuls les niveaux actifs sont affichés ; « Afficher les inactifs » permet de les réactiver."""
    inactifs = request.GET.get('inactifs') == '1'
    niveaux = Niveau.objects.all() if inactifs else Niveau.actifs()
    from django.db.models import Count, Q
    from parametres.utils import get_annee_courante
    niveaux = niveaux.annotate(effectif=Count('etudiants', filter=Q(etudiants__annee=get_annee_courante())))
    return render(request, 'niveaux/liste.html', {
        'niveaux': niveaux, 'inactifs': inactifs, 'nb_inactifs': Niveau.objects.filter(actif=False).count()})


@gestionnaire_requis
def niveau_creer(request):
    form = NiveauForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, _("Niveau créé."))
        return redirect('niveau_liste')
    return render(request, 'niveaux/form.html', {'form': form, 'titre': _("Nouveau niveau")})


@gestionnaire_requis
def niveau_modifier(request, pk):
    niveau = get_object_or_404(Niveau, pk=pk)
    form = NiveauForm(request.POST or None, instance=niveau)
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, _("Niveau modifié."))
        return redirect('niveau_liste')
    return render(request, 'niveaux/form.html', {'form': form, 'titre': _("Modifier le niveau"), 'niveau': niveau})


@gestionnaire_requis
@require_POST
def niveau_basculer(request, pk):
    """Active / désactive un niveau (il n'est jamais supprimé)."""
    niveau = get_object_or_404(Niveau, pk=pk)
    niveau.actif = not niveau.actif
    niveau.save(update_fields=['actif'])
    messages.success(request, _("Niveau activé.") if niveau.actif else _("Niveau désactivé."))
    return redirect('niveau_liste')
