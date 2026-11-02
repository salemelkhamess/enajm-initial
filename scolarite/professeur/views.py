# views.py
from django.urls import reverse_lazy
from django.views.generic import ListView, CreateView, UpdateView, DeleteView

from entete.models import Entete
from pointage.models import Pointage
from pointagematiere.models import PointageMatiere
from .forms import ProfesseurForm
from django.utils import timezone
from django.db.models import Count, Q, Sum
from django.db.models.functions import Coalesce

from django.shortcuts import get_object_or_404, render
from django.utils import timezone
from professeur.models import Professeur, AttestationCounter, AttestationEnseignement
from django.db.models import Count, Q

class ProfesseurListView(ListView):
    model = Professeur
    template_name = 'professeur/professeur_list.html'
    context_object_name = 'professeurs'

class ProfesseurCreateView(CreateView):
    model = Professeur
    form_class = ProfesseurForm
    template_name = 'professeur/professeur_form.html'
    success_url = reverse_lazy('professeur_list')

class ProfesseurUpdateView(UpdateView):
    model = Professeur
    form_class = ProfesseurForm
    template_name = 'professeur/professeur_form.html'
    success_url = reverse_lazy('professeur_list')

class ProfesseurDeleteView(DeleteView):
    model = Professeur
    template_name = 'professeur/professeur_confirm_delete.html'
    success_url = reverse_lazy('professeur_list')


def certificat_enseignement(request, pk):
    professor = get_object_or_404(Professeur, pk=pk)

    # Cette ligne va soit récupérer l'attestation existante, soit en créer une nouvelle
    # avec un numéro incrémenté (une seule fois)
    attestation = AttestationEnseignement.get_or_create_for_professor(professor)

    # Récupérer les pointages (votre code existant)
    pointages_standard = Pointage.objects.filter(
        professeur=professor,
        etat='present'
    ).values(
        'annee__numero_annee',
        'trimestre__numero_trimestre',
        'trimestre__nom_ar',
        'seance__matiere__nom',
        'seance__secteur__nom'
    ).annotate(
        nombre_seances_standard=Count('id')
    )

    pointages_matiere = PointageMatiere.objects.filter(
        professeur=professor,
        etat=PointageMatiere.Etat.EFFECTUE
    ).values(
        'annee__numero_annee',
        'trimestre__numero_trimestre',
        'trimestre__nom_ar',
        'matiere__nom',
        'secteur__nom'
    ).annotate(
        nombre_seances_matiere=Count('id')
    )

    enseignements = {}

    # Traiter les pointages (votre code existant)
    for pointage in pointages_standard:
        key = (
            pointage['annee__numero_annee'],
            pointage['trimestre__numero_trimestre'],
            pointage['trimestre__nom_ar'],
            pointage['seance__matiere__nom'],
            pointage['seance__secteur__nom']
        )
        if key not in enseignements:
            enseignements[key] = {
                'annee': pointage['annee__numero_annee'],
                'trimestre_num': pointage['trimestre__numero_trimestre'],
                'trimestre_nom': pointage['trimestre__nom_ar'],
                'matiere': pointage['seance__matiere__nom'],
                'secteur': pointage['seance__secteur__nom'],
                'total_seances': pointage['nombre_seances_standard']
            }
        else:
            enseignements[key]['total_seances'] += pointage['nombre_seances_standard']

    for pointage in pointages_matiere:
        key = (
            pointage['annee__numero_annee'],
            pointage['trimestre__numero_trimestre'],
            pointage['trimestre__nom_ar'],
            pointage['matiere__nom'],
            pointage['secteur__nom']
        )
        if key not in enseignements:
            enseignements[key] = {
                'annee': pointage['annee__numero_annee'],
                'trimestre_num': pointage['trimestre__numero_trimestre'],
                'trimestre_nom': pointage['trimestre__nom_ar'],
                'matiere': pointage['matiere__nom'],
                'secteur': pointage['secteur__nom'],
                'total_seances': pointage['nombre_seances_matiere']
            }
        else:
            enseignements[key]['total_seances'] += pointage['nombre_seances_matiere']

    enseignements_list = list(enseignements.values())
    enseignements_list.sort(key=lambda x: (x['annee'], x['trimestre_num'], x['matiere']))

    context = {
        'professor': professor,
        'enseignements': enseignements_list,
        'today': timezone.now().date(),
        'cert_number': attestation.numero,
        'entete' : Entete.objects.filter(id=1)
    }

    return render(request, 'professeur/certificat_template.html', context)