from django.shortcuts import render
from django.utils.translation import get_language
from django.views.generic import ListView, CreateView, UpdateView, DeleteView
from django.urls import reverse_lazy

from annee.models import Annee
from branches.models import Secteur
from entete.models import Entete
from trimestre.models import Trimestre
from .models import PV
from .forms import PVForm
from django.views import View

from django.shortcuts import render, get_object_or_404
from django.http import HttpResponse
from django.template.loader import render_to_string
from django.utils import timezone

class PVListView(ListView):
    model = PV
    template_name = 'pv/list.html'
    context_object_name = 'pvs'
    ordering = ['-date_creation']


class PVCreateView(CreateView):
    model = PV
    form_class = PVForm
    template_name = 'pv/form.html'
    success_url = reverse_lazy('pv_list')
    extra_context = {'title': 'Créer un PV'}

class PVUpdateView(UpdateView):
    model = PV
    form_class = PVForm
    template_name = 'pv/form.html'
    success_url = reverse_lazy('pv_list')
    extra_context = {'title': 'Modifier le PV'}

class PVDeleteView(DeleteView):
    model = PV
    template_name = 'pv/delete_confirm.html'
    success_url = reverse_lazy('pv_list')

class PVRapportView(View):
    def get(self, request):
        date_debut = request.GET.get('date_debut')
        date_fin = request.GET.get('date_fin')
        annee_id = request.GET.get('annee')
        trimestre_id = request.GET.get('trimestre')
        secteur_id = request.GET.get('secteur')

        pvs = PV.objects.all()

        # Filtrer par date si fournies
        if date_debut and date_fin:
            pvs = pvs.filter(date_creation__range=[date_debut, date_fin])

        # Récupérer la liste complète des options pour le formulaire
        annees = Annee.objects.all()
        trimestres = Trimestre.objects.all()
        secteurs = Secteur.objects.all()

        # Filtrer les PV via étudiants selon annee, trimestre et secteur
        if annee_id:
            pvs = pvs.filter(etudiant__annee_id=annee_id)
            trimestres = trimestres.filter(annee_id=annee_id)  # Optionnel : ne montrer que trimestres de l'année choisie

        if trimestre_id:
            pvs = pvs.filter(date_creation__range=[Trimestre.objects.get(pk=trimestre_id).debut,
                                                   Trimestre.objects.get(pk=trimestre_id).fin])

        if secteur_id:
            pvs = pvs.filter(etudiant__secteur_id=secteur_id)

        entete = Entete.objects.first()

        return render(request, 'pv/pv_rapport.html', {
            'pvs': pvs,
            'date_debut': date_debut,
            'date_fin': date_fin,
            'entete': entete,
            'annees': annees,
            'trimestres': trimestres,
            'secteurs': secteurs,
            'annee_id': annee_id,
            'trimestre_id': trimestre_id,
            'secteur_id': secteur_id,
            'langue': get_language()

        })





def pv_triche(request, pv_id):
    pv = get_object_or_404(PV, pk=pv_id, type='triche')

    context = {
        'pv': pv,
        'annee_scolaire': "2024-2025",
        'date_emission': timezone.now().strftime("%d/%m/%Y"),
        'current_date': timezone.now().strftime("%Y-%m-%d"),
    }

    if request.GET.get('format') == 'pdf':
        html = render_to_string('pv/pv_triche.html', context)
        # Ici vous devriez utiliser une librairie comme WeasyPrint pour générer le PDF
        return HttpResponse(html)

    return render(request, 'pv/pv_triche.html', context)