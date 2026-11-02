from django.http import JsonResponse
from django.views.generic import ListView, CreateView, UpdateView, DeleteView
from django.urls import reverse_lazy

from annee.models import Annee
from branches.models import Secteur
from entete.models import Entete
from parametres.models import Parametres
from presenceetudiant.models import PresenceEtudiant
from trimestre.models import Trimestre
from .models import Etudiant
from .forms import EtudiantForm
from django.views.generic import DetailView
from django.utils import timezone
import ast  # pour convertir une chaîne en liste Python en toute sécurité
from django.utils.translation import gettext_lazy as _
from django.db.models import Count, F, Q
from parametres.utils import get_annee_courante
from presenceetudiant.models import q_comptee
from django.shortcuts import render, get_object_or_404
from django.http import HttpResponse
from django.template.loader import render_to_string
from django.http import Http404
from django.db.models import Count
from datetime import datetime
from django.shortcuts import render
from django.utils.translation import get_language

class EtudiantListView(ListView):
    model = Etudiant
    template_name = 'etudiants/list.html'
    context_object_name = 'etudiants'

    def get_queryset(self):
        return (super().get_queryset().filter(annee=get_annee_courante())
                .select_related('annee', 'secteur__formation'))

class EtudiantCreateView(CreateView):
    model = Etudiant
    form_class = EtudiantForm
    template_name = 'etudiants/create.html'
    success_url = reverse_lazy('etudiant_list')

class EtudiantUpdateView(UpdateView):
    model = Etudiant
    form_class = EtudiantForm
    template_name = 'etudiants/edit.html'
    success_url = reverse_lazy('etudiant_list')

class EtudiantDeleteView(DeleteView):
    model = Etudiant
    template_name = 'etudiants/delete.html'
    success_url = reverse_lazy('etudiant_list')



class AttestationView(DetailView):
    model = Etudiant
    template_name = 'etudiants/attestation.html'
    context_object_name = 'etudiant'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # Récupération de l'étudiant
        etudiant = context['etudiant']

        # Vérifie si le champ 'diplomes' est une chaîne, et essaie de le convertir en liste
        if isinstance(etudiant.diplomes, str):
            try:
                etudiant.diplomes = ast.literal_eval(etudiant.diplomes)
            except Exception:
                etudiant.diplomes = []

        context['date'] = timezone.now().date()
        return context


class EtudiantRegistrationView(DetailView):
    model = Etudiant
    template_name = 'etudiants/registration_form.html'
    context_object_name = 'etudiant'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # Récupération de l'étudiant
        etudiant = context['etudiant']

        # Vérifie si le champ 'diplomes' est une chaîne, et essaie de le convertir en liste
        if isinstance(etudiant.diplomes, str):
            try:
                etudiant.diplomes = ast.literal_eval(etudiant.diplomes)
            except Exception:
                etudiant.diplomes = []

        context['form_title'] = _("REGISTRATION AND COMMITMENT FORM")
        return context


def liste_etudiants_par_secteur(request):
    """
    Vue pour afficher la liste des étudiants par secteur avec filtrage
    """
    # Récupération des paramètres de filtre
    selected_annee = request.GET.get('annee')
    selected_trimestre = request.GET.get('trimestre')
    selected_secteur = request.GET.get('secteur')

    # Récupération de toutes les données pour les formulaires
    annees = Annee.objects.all().order_by('numero_annee')
    trimestres = Trimestre.objects.all().order_by('numero_trimestre')
    secteurs = Secteur.objects.all()

    # Initialisation des variables
    etudiants = []
    stats_sexe = []
    selected_annee_obj = None
    selected_trimestre_obj = None
    selected_secteur_obj = None

    # Si tous les filtres sont sélectionnés
    if selected_annee and selected_trimestre and selected_secteur:
        try:
            selected_annee_obj = Annee.objects.get(id=selected_annee)
            selected_trimestre_obj = Trimestre.objects.get(id=selected_trimestre)
            selected_secteur_obj = Secteur.objects.get(id=selected_secteur)

            # Filtrage des étudiants
            etudiants = Etudiant.objects.filter(
                annee_id=selected_annee,
                secteur_id=selected_secteur
            ).order_by('nom', 'prenom')

            # Calcul des statistiques par sexe
            stats_sexe = etudiants.values('sexe').annotate(count=Count('sexe')).order_by('sexe')

        except (Annee.DoesNotExist, Trimestre.DoesNotExist, Secteur.DoesNotExist):
            pass

    # Si seulement l'année est sélectionnée, filtrer les trimestres
    if selected_annee:
        try:
            annee_obj = Annee.objects.get(id=selected_annee)
            trimestres = Trimestre.objects.filter(annee=annee_obj).order_by('numero_trimestre')
        except Annee.DoesNotExist:
            pass

    context = {
        'annees': annees,
        'trimestres': trimestres,
        'secteurs': secteurs,
        'etudiants': etudiants,
        'stats_sexe': stats_sexe,
        'selected_annee': selected_annee,
        'selected_trimestre': selected_trimestre,
        'selected_secteur': selected_secteur,
        'selected_annee_obj': selected_annee_obj,
        'selected_trimestre_obj': selected_trimestre_obj,
        'selected_secteur_obj': selected_secteur_obj,
        'entete': None,  # Vous pouvez ajouter votre entête ici
    }

    return render(request, 'etudiants/liste_par_secteur.html', context)


def get_trimestres(request):
    """
    Vue AJAX pour récupérer les trimestres d'une année donnée
    """
    annee_id = request.GET.get('annee_id')
    trimestres = []

    if annee_id:
        try:
            annee = Annee.objects.get(id=annee_id)
            trimestres_qs = Trimestre.objects.filter(annee=annee).order_by('numero_trimestre')

            for trimestre in trimestres_qs:
                # Détermine la langue courante
                if request.LANGUAGE_CODE in ['ar', 'ar-ma']:
                    nom = trimestre.nom_ar
                else:
                    nom = trimestre.nom_fr

                trimestres.append({
                    'id': trimestre.id,
                    'nom': nom
                })
        except Annee.DoesNotExist:
            pass

    return JsonResponse({'trimestres': trimestres})



def attestation_inscription(request, etudiant_id):
    etudiant = get_object_or_404(Etudiant, pk=etudiant_id)

    context = {
        'etudiant': etudiant,
        'annee_scolaire': "2024-2025",
        'ordre': "01-2025",
        'date_emission': ".....................",
    }

    if request.GET.get('format') == 'pdf':
        html = render_to_string('etudiants/attestation_inscription.html', context)
        # Ici vous devriez utiliser une librairie comme WeasyPrint pour générer le PDF
        return HttpResponse(html)

    return render(request, 'etudiants/attestation_inscription.html', context)


def carte_etudiant(request, matricule):
    etudiant = get_object_or_404(Etudiant, matricule=matricule)

    # Vérifier si l'étudiant a les informations nécessaires
    if not etudiant.nni or not etudiant.secteur:
        raise Http404("Les informations de l'étudiant sont incomplètes pour générer la carte")

    context = {
        'etudiant': etudiant,
    }
    return render(request, 'etudiants/carte_etudiant.html', context)


def dashboard_view(request):
    secteurs_etudiants = Secteur.objects.annotate(
        num_etudiants=Count('etudiants', filter=Q(etudiants__annee=get_annee_courante()))
    ).values('id', 'nom', 'num_etudiants').order_by('nom')

    context = {
        'secteurs_etudiants': [{
            'number': s['num_etudiants'],
            'label': s['nom'],
            'icon': 'ion-ios-people',
            'link': f'/etudiants/secteur/{s["id"]}/'  # Changé 'url' en 'link'
        } for s in secteurs_etudiants]
    }
    return render(request, 'etudiants/student_by_class.html', context)


class EtudiantsParSecteurListView(ListView):
    model = Etudiant
    template_name = 'etudiants/student_by_class.html'
    context_object_name = 'etudiants'

    def get_queryset(self):
        secteur_id = self.kwargs['secteur_id']
        return Etudiant.objects.filter(secteur_id=secteur_id, annee=get_annee_courante()).order_by('nom')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['secteur'] = Secteur.objects.get(id=self.kwargs['secteur_id'])
        return context

def rapport_absence_etudiants(request):
    date_debut = request.GET.get('date_debut')
    date_fin = request.GET.get('date_fin')
    presences = PresenceEtudiant.objects.all()

    if date_debut and date_fin:
        try:
            debut = datetime.strptime(date_debut, '%Y-%m-%d').date()
            fin = datetime.strptime(date_fin, '%Y-%m-%d').date()
            presences = presences.filter(date_cours__range=(debut, fin))
        except ValueError:
            debut = fin = None
    else:
        debut = fin = None

    # Comptage des absences par étudiant
    absences_par_etudiant = (
        PresenceEtudiant.objects
        .filter(q_comptee())
        .filter(date_cours__range=(debut, fin)) if debut and fin else
        PresenceEtudiant.objects.filter(q_comptee())
    ).values(
        'etudiant__matricule',
        'etudiant__nom',
        'etudiant__prenom'
    ).annotate(total_absences=Count('id'))

    context = {
        'presences': presences,
        'absences_par_etudiant': absences_par_etudiant,
        'date_debut': debut,
        'date_fin': fin,
        'date_debut_str': date_debut,
        'date_fin_str': date_fin,
        'entete': Entete.objects.first(),
        'langue': get_language()
    }
    return render(request, 'etudiants/rapport_absence_etudiants.html', context)


class AbsencesEtudiantView(DetailView):
    model = Etudiant
    template_name = 'etudiants/detail_absences_etudiant.html'
    context_object_name = 'etudiant'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        params = Parametres.get_instance()

        # Récupérer les absences groupées par matière
        absences_par_matiere = PresenceEtudiant.objects.filter(
            q_comptee(),
            etudiant=self.object,
            annee=params.annee_courante,
            trimestre=params.trimestre_courant
        ).values(
            'matiere__id',
            'matiere__nom'
        ).annotate(
            total_absences=Count('id'),
            total_heures=F('total_absences') * 2  # 1 absence = 2 heures
        ).order_by('matiere__nom')

        # Calcul des totaux généraux
        total_absences = sum(item['total_absences'] for item in absences_par_matiere)
        total_heures = total_absences * 2
        context['entete'] = Entete.objects.filter(id=1)

        context.update({
            'absences_par_matiere': absences_par_matiere,
            'total_absences': total_absences,
            'total_heures': total_heures,
            'annee_courante': params.annee_courante,
            'trimestre_courant': params.trimestre_courant
        })
        return context