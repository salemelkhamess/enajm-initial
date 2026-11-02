from django.shortcuts import render

# Create your views here.

# parametres/views.py
from django.utils.translation import gettext_lazy as _
from django.views.generic import UpdateView
from django.urls import reverse_lazy
from django.contrib.messages.views import SuccessMessageMixin
from .models import Parametres
from .forms import ParametresForm

from django.http import JsonResponse
from trimestre.models import Trimestre
from annee.models import Annee
from django.shortcuts import redirect
from django.views.decorators.http import require_POST
from django.utils.http import url_has_allowed_host_and_scheme
from .middleware import SESSION_KEY


class ParametresUpdateView(SuccessMessageMixin, UpdateView):
    model = Parametres
    form_class = ParametresForm
    template_name = 'parametres/parametres_form.html'
    success_url = reverse_lazy('update_params')
    success_message = _("Les paramètres ont été mis à jour avec succès")

    def form_valid(self, form):
        # la consultation suit à nouveau l'année active qui vient d'être définie
        self.request.session.pop(SESSION_KEY, None)
        return super().form_valid(form)

    def get_object(self, queryset=None):
        return Parametres.get_real_instance()


def get_trimestres(request):
    annee_id = request.GET.get('annee_id')
    trimestres = Trimestre.objects.filter(annee_id=annee_id)
    options = '<option value="">---------</option>'
    for t in trimestres:
        options += f'<option value="{t.id}">{t.nom}</option>'
    return JsonResponse(options, safe=False)


@require_POST
def set_annee_consultee(request):
    """Choisit l'année dont on consulte les données (vide = année active)."""
    annee_id = request.POST.get('annee_id')
    if annee_id and Annee.objects.filter(pk=annee_id).exists() \
            and int(annee_id) != Parametres.get_real_instance().annee_courante_id:
        request.session[SESSION_KEY] = int(annee_id)
    else:
        request.session.pop(SESSION_KEY, None)
    nxt = request.POST.get('next') or '/'
    if not url_has_allowed_host_and_scheme(nxt, allowed_hosts={request.get_host()}):
        nxt = '/'
    return redirect(nxt)
