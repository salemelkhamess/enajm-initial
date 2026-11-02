from django.views.generic import ListView, CreateView, UpdateView, DeleteView
from django.urls import reverse_lazy

from annee.models import Annee
from branches.models import Secteur
from etudiant.models import Etudiant
from matiers.models import Matiere
from trimestre.models import Trimestre
from .models import Evaluation
from .forms import EvaluationForm
from django.http import JsonResponse
from trimestre.models import Trimestre


class EvaluationListView(ListView):
    model = Evaluation
    template_name = 'evaluations/evaluation_list.html'
    context_object_name = 'evaluations'


class EvaluationCreateView(CreateView):
    model = Evaluation
    form_class = EvaluationForm
    template_name = 'evaluations/evaluation_form.html'
    success_url = reverse_lazy('evaluation_list')


class EvaluationUpdateView(UpdateView):
    model = Evaluation
    form_class = EvaluationForm
    template_name = 'evaluations/evaluation_form.html'
    success_url = reverse_lazy('evaluation_list')


class EvaluationDeleteView(DeleteView):
    model = Evaluation
    template_name = 'evaluations/evaluation_confirm_delete.html'
    success_url = reverse_lazy('evaluation_list')


class EvaluationCreateFormView(CreateView):
    model = Evaluation
    form_class = EvaluationForm
    template_name = 'evaluations/fpc.html'
    success_url = reverse_lazy('evaluation_list')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # Récupérer les paramètres de filtrage
        annee_id = self.request.GET.get('annee')
        trimestre_id = self.request.GET.get('trimestre')
        secteur_id = self.request.GET.get('secteur')
        matiere_id = self.request.GET.get('matiere')
        selected_date = self.request.GET.get('date')
        selected_heure = self.request.GET.get('heure')

        # Filtrer les étudiants
        etudiants = Etudiant.objects.all()
        if annee_id:
            etudiants = etudiants.filter(annee_id=annee_id)
        if secteur_id:
            etudiants = etudiants.filter(secteur_id=secteur_id)

        # Récupérer l'objet Matiere (optionnel)
        selected_matiere = None
        if matiere_id:
            try:
                selected_matiere = Matiere.objects.get(id=matiere_id)
            except Matiere.DoesNotExist:
                selected_matiere = None

        context.update({
            'etudiants': etudiants,
            'annees': Annee.objects.all(),
            'trimestres': Trimestre.objects.filter(annee_id=annee_id) if annee_id else Trimestre.objects.none(),
            'secteurs': Secteur.objects.all(),
            'matieres': Matiere.objects.all(),

            'selected_annee': int(annee_id) if annee_id else None,
            'selected_trimestre': int(trimestre_id) if trimestre_id else None,
            'selected_secteur': Secteur.objects.get(id=secteur_id) if secteur_id else None,
            'selected_matiere': selected_matiere,
            'selected_date': selected_date,
            'selected_heure': selected_heure,
            'langue': self.request.LANGUAGE_CODE,
        })

        return context



def load_trimestres(request):
    annee_id = request.GET.get('annee_id')
    trimestres = Trimestre.objects.filter(annee_id=annee_id)
    return JsonResponse([{'id': t.id, 'nom_fr': t.nom} for t in trimestres], safe=False)