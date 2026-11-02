from datetime import datetime

from django.shortcuts import render
from django.urls import reverse_lazy
from django.utils.translation import get_language
from django.views.generic import ListView, CreateView, UpdateView, DeleteView

from entete.models import Entete
from pointage.models import Pointage
from pointagematiere.models import PointageMatiere
from .models import PresenceProfesseur
from .forms import PresenceProfesseurForm
from django.db.models import Count, Q

class PresenceListView(ListView):
    model = PresenceProfesseur
    template_name = 'presence/professeur_list.html'
    context_object_name = 'presences'


class PresenceCreateView(CreateView):
    model = PresenceProfesseur
    form_class = PresenceProfesseurForm
    template_name = 'presence/professeur_form.html'
    success_url = reverse_lazy('presence_list')

class PresenceUpdateView(UpdateView):
    model = PresenceProfesseur
    form_class = PresenceProfesseurForm
    template_name = 'presence/professeur_form.html'
    success_url = reverse_lazy('presence_list')

class PresenceDeleteView(DeleteView):
    model = PresenceProfesseur
    template_name = 'presence/professeur_confirm_delete.html'
    success_url = reverse_lazy('presence_list')


def rapport_presence_professeurs(request):
    date_debut = request.GET.get('date_debut')
    date_fin = request.GET.get('date_fin')
    pointages = Pointage.objects.all()
    pointages_matieres = PointageMatiere.objects.filter(etat='EF')  # Cours effectués

    if date_debut and date_fin:
        try:
            debut = datetime.strptime(date_debut, '%Y-%m-%d').date()
            fin = datetime.strptime(date_fin, '%Y-%m-%d').date()
            pointages = pointages.filter(date__range=(debut, fin))
            pointages_matieres = pointages_matieres.filter(date_cours__range=(debut, fin))
        except ValueError:
            debut = fin = None
    else:
        debut = fin = None

    # Préparer une liste combinée pour le template
    presences_combinees = []

    # Ajouter les pointages normaux
    for p in pointages:
        presences_combinees.append({
            'type': 'pointage',
            'date': p.date,
            'heure_debut': p.seance.heure_debut if p.seance else None,
            'heure_fin': p.seance.heure_fin if p.seance else None,
            'secteur': p.seance.secteur.nom if p.seance and p.seance.secteur else '',
            'matiere': p.seance.matiere.nom if p.seance and p.seance.matiere else '',
            'professeur': f"{p.professeur.nom} {p.professeur.prenom}",
            'etat': p.etat,
            'contenu': None
        })

    # Ajouter les pointages matières (avec état "présent")
    for pm in pointages_matieres:
        presences_combinees.append({
            'type': 'pointage_matiere',
            'date': pm.date_cours,
            'heure_debut': pm.heure_debut,
            'heure_fin': pm.heure_fin,
            'secteur': pm.secteur.nom,
            'matiere': pm.matiere.nom,
            'professeur': f"{pm.professeur.nom} {pm.professeur.prenom}",
            'etat': 'present',  # On considère EF comme "présent"
            'contenu': pm.contenu
        })

    # Trier par date et heure
    presences_combinees.sort(key=lambda x: (x['date'], x['heure_debut']))

    # Comptage des absences par professeur
    absences_par_professeur = (
        Pointage.objects
        .filter(etat='absent')
        .filter(date__range=(debut, fin)) if debut and fin else
        Pointage.objects.filter(etat='absent')
    ).values('professeur__nom', 'professeur__prenom').annotate(total_absences=Count('id'))

    context = {
        'presences_combinees': presences_combinees,
        'absences_par_professeur': absences_par_professeur,
        'date_debut': debut,
        'date_fin': fin,
        'date_debut_str': date_debut,
        'date_fin_str': date_fin,
        'entete': Entete.objects.first(),
        'langue': get_language()
    }
    return render(request, 'presence/rapport_presence_professeurs.html', context)