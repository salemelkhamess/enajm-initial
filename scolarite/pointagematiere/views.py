from django.contrib import messages
from django.views.generic import ListView, CreateView, UpdateView, DeleteView
from django.urls import reverse_lazy
from django.utils.translation import gettext_lazy as _, get_language
from django.contrib.messages.views import SuccessMessageMixin
from django.db.models import Count

from annee.models import Annee
from branches.models import Secteur
from matiers.models import Matiere
from trimestre.models import Trimestre
from .models import PointageMatiere
from .forms import PointageMatiereForm
from django.http import JsonResponse


class PointageMatiereListView(ListView):
    model = PointageMatiere
    template_name = 'pointage_matiere/list.html'
    context_object_name = 'pointages'

    def get_queryset(self):
        return PointageMatiere.objects.all().order_by('-date_cours')


class PointageMatiereCreateView(SuccessMessageMixin, CreateView):
    model = PointageMatiere
    form_class = PointageMatiereForm
    template_name = 'pointage_matiere/form.html'
    success_url = reverse_lazy('pointage_matiere_list')
    success_message = _("Pointage matière créé avec succès")

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['lang'] = get_language()
        return kwargs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['lang'] = get_language()  # Passer la langue au template
        return context


class PointageMatiereUpdateView(SuccessMessageMixin, UpdateView):
    model = PointageMatiere
    form_class = PointageMatiereForm
    template_name = 'pointage_matiere/form.html'
    success_url = reverse_lazy('pointage_matiere_list')
    success_message = _("Pointage matière mis à jour avec succès")

class PointageMatiereDeleteView(SuccessMessageMixin, DeleteView):
    model = PointageMatiere
    template_name = 'pointage_matiere/confirm_delete.html'
    success_url = reverse_lazy('pointage_matiere_list')
    success_message = _("Pointage matière supprimé avec succès")

    def delete(self, request, *args, **kwargs):
        messages.success(self.request, self.success_message)
        return super().delete(request, *args, **kwargs)


class RapportPointageListView(ListView):
    model = PointageMatiere
    template_name = 'pointage_matiere/rapport_pointage.html'
    context_object_name = 'pointages'

    def get_queryset(self):
        queryset = super().get_queryset()

        # Filtrage
        annee_id = self.request.GET.get('annee')
        trimestre_id = self.request.GET.get('trimestre')
        secteur_id = self.request.GET.get('secteur')
        etat = self.request.GET.get('etat')

        if annee_id:
            queryset = queryset.filter(annee_id=annee_id)
        if trimestre_id:
            queryset = queryset.filter(trimestre_id=trimestre_id)
        if secteur_id:
            queryset = queryset.filter(secteur_id=secteur_id)
        if etat:
            queryset = queryset.filter(etat=etat)

        return queryset.select_related('annee', 'trimestre', 'secteur', 'matiere', 'professeur')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # Stats pour le résumé
        context['stats'] = self.get_queryset().values('etat').annotate(
            total=Count('id')
        )

        # Options de filtrage
        context['annees'] = Annee.objects.all()
        context['trimestres'] = Trimestre.objects.all()
        context['secteurs'] = Secteur.objects.all()
        context['etats'] = PointageMatiere.Etat.choices

        # Valeurs sélectionnées
        context['selected_annee'] = self.request.GET.get('annee')
        context['selected_trimestre'] = self.request.GET.get('trimestre')
        context['selected_secteur'] = self.request.GET.get('secteur')
        context['selected_etat'] = self.request.GET.get('etat')

        return context

def get_trimestres(request):
    annee_id = request.GET.get('annee_id')
    trimestres = Trimestre.objects.filter(annee_id=annee_id)
    return JsonResponse([{'id': t.id, 'nom_fr': t.nom} for t in trimestres], safe=False)

def get_matieres(request):
    secteur_id = request.GET.get('secteur_id')
    matieres = Matiere.objects.filter(secteur_id=secteur_id).values('id', 'nom')
    return JsonResponse(list(matieres), safe=False)