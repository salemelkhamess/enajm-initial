from django.utils.translation import gettext as _
# emploi/views.py
from django.contrib import messages
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, render, redirect
from django.urls import reverse_lazy
from django.utils.translation import get_language
from django.views import View
from django.views.generic import ListView, CreateView, UpdateView, DeleteView

from annee.models import Annee
from branches.models import Secteur
from entete.models import Entete
from matiers.models import Matiere
from parametres.models import Parametres
from professeur.models import Professeur
from salle.models import Salle
from trimestre.models import Trimestre
from .models import EmploiDuTemps
from .forms import EmploiDuTempsForm, EmploiParametresForm
from django.core.exceptions import ValidationError
from django.db.models import Prefetch

class EmploiListView(ListView):
    model = EmploiDuTemps
    template_name = 'emploi/list.html'
    context_object_name = 'secteurs_emplois'

    def get_queryset(self):
        # Récupérer tous les secteurs avec leurs emplois du temps
        return Secteur.objects.prefetch_related(
            Prefetch('emploidutemps_set',
                    queryset=EmploiDuTemps.objects.select_related('matiere', 'professeur', 'salle')
                    .order_by('jour', 'heure_debut')))

class EmploiCreateView(CreateView):
    model = EmploiDuTemps
    form_class = EmploiDuTempsForm
    template_name = 'emploi/form.html'
    success_url = reverse_lazy('emploi_liste')
    def form_valid(self, form):
        try:
            return super().form_valid(form)
        except ValidationError as e:
            form.add_error(None, e)
            return self.form_invalid(form)


class EmploiUpdateView(UpdateView):
    model = EmploiDuTemps
    form_class = EmploiDuTempsForm
    template_name = 'emploi/form.html'
    success_url = reverse_lazy('emploi_liste')
    def form_valid(self, form):
        try:
            return super().form_valid(form)
        except ValidationError as e:
            form.add_error(None, e)
            return self.form_invalid(form)

class EmploiDeleteView(DeleteView):
    model = EmploiDuTemps
    template_name = 'emploi/delete_confirm.html'
    success_url = reverse_lazy('emploi_liste')


class EmploiGrilleView(View):
    template_name = 'emploi/grille_edition.html'

    def get(self, request):
        form = EmploiParametresForm(request.GET or None)
        if 'secteur' in request.GET:
            return self.process_form(request)
        return render(request, self.template_name, {'form': form})

    def post(self, request):
        return self.process_form(request)

    def process_form(self, request):
        data = request.POST if request.method == 'POST' else request.GET
        form = EmploiParametresForm(data)

        if form.is_valid():

            annee = form.cleaned_data['annee']
            trimestre = form.cleaned_data['trimestre']
            secteur = form.cleaned_data['secteur']

            # Créneaux horaires fixes
            creneaux = [
                {'debut': '08:00', 'fin': '10:00'},
                {'debut': '10:00', 'fin': '12:00'},
                {'debut': '12:00', 'fin': '14:00'},
            ]

            # Jours de la semaine
            jours = ['Lundi', 'Mardi', 'Mercredi', 'Jeudi', 'Vendredi']

            # Récupérer les données nécessaires
            matieres = Matiere.objects.all()
            professeurs = Professeur.objects.all()
            salles = Salle.objects.all()

            # Préparer les emplois existants
            emplois_existants = {}
            for jour in jours:
                emplois_existants[jour] = {}
                for creneau in creneaux:
                    emploi = EmploiDuTemps.objects.filter(
                        annee=annee,
                        trimestre=trimestre,
                        secteur=secteur,
                        jour=jour,
                        heure_debut=creneau['debut'],
                        heure_fin=creneau['fin']
                    ).first()
                    emplois_existants[jour][f"{creneau['debut']}-{creneau['fin']}"] = emploi

            return render(request, self.template_name, {
                'form': form,
                'show_grille': True,
                'annee': annee,
                'trimestre': trimestre,
                'secteur': secteur,
                'creneaux': creneaux,
                'jours': jours,
                'matieres': matieres,
                'professeurs': professeurs,
                'salles': salles,
                'emplois_existants': emplois_existants,
            })

        return render(request, self.template_name, {'form': form})


class SauvegarderGrilleView(View):
    def post(self, request):
        try:
            parametres = Parametres.get_instance()
            data = request.POST
            annee_id = parametres.annee_courante.id  # Correct (avec "e")
            trimestre_id = parametres.trimestre_courant.id  # Correct (sans "e")

            secteur_id = data.get('secteur_id')

            # Supprimer les anciens emplois
            EmploiDuTemps.objects.filter(
                annee_id=annee_id,
                trimestre_id=trimestre_id,
                secteur_id=secteur_id
            ).delete()

            # Jours de la semaine
            jours = ['Lundi', 'Mardi', 'Mercredi', 'Jeudi', 'Vendredi']

            # Sauvegarder les créneaux fixes
            creneau_debuts = data.getlist('creneau_debut[]')
            creneau_fins = data.getlist('creneau_fin[]')

            for i in range(len(creneau_debuts)):
                debut = creneau_debuts[i]
                fin = creneau_fins[i]

                for jour in jours:
                    matiere_id = data.get(f'matiere_{jour}_{debut}_{fin}')
                    professeur_id = data.get(f'professeur_{jour}_{debut}_{fin}')
                    salle_id = data.get(f'salle_{jour}_{debut}_{fin}')

                    if matiere_id and professeur_id and salle_id:
                        EmploiDuTemps.objects.create(
                            annee_id=annee_id,
                            trimestre_id=trimestre_id,
                            secteur_id=secteur_id,
                            matiere_id=matiere_id,
                            professeur_id=professeur_id,
                            salle_id=salle_id,
                            jour=jour,
                            heure_debut=debut,
                            heure_fin=fin
                        )

            # Sauvegarder les nouveaux créneaux ajoutés
            new_debut = data.get('new_creneau_debut')
            new_fin = data.get('new_creneau_fin')

            if new_debut and new_fin:
                for jour in jours:
                    matiere_id = data.get(f'new_matiere_{jour}')
                    professeur_id = data.get(f'new_professeur_{jour}')
                    salle_id = data.get(f'new_salle_{jour}')

                    if matiere_id and professeur_id and salle_id:
                        EmploiDuTemps.objects.create(
                            annee_id=annee_id,
                            trimestre_id=trimestre_id,
                            secteur_id=secteur_id,
                            matiere_id=matiere_id,
                            professeur_id=professeur_id,
                            salle_id=salle_id,
                            jour=jour,
                            heure_debut=new_debut,
                            heure_fin=new_fin
                        )

            return JsonResponse({'success': True})

        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)}, status=400)


class EmploiGrilleEditView(View):
    template_name = 'emploi/grille_edition_edit.html'

    def get(self, request, pk):
        emploi = get_object_or_404(EmploiDuTemps, pk=pk)

        # Créneaux horaires fixes
        creneaux = [
            {'debut': '08:00', 'fin': '10:00'},
            {'debut': '10:00', 'fin': '12:00'},
            {'debut': '12:00', 'fin': '14:00'},
        ]

        # Jours de la semaine
        jours = ['Lundi', 'Mardi', 'Mercredi', 'Jeudi', 'Vendredi']

        # Récupérer les données nécessaires
        matieres = Matiere.objects.all()
        professeurs = Professeur.objects.all()
        salles = Salle.objects.all()

        # Préparer les données existantes sous une forme plus simple
        emplois_existants = {}
        for jour in jours:
            emplois_existants[jour] = {}
            for creneau in creneaux:
                creneau_str = f"{creneau['debut']}-{creneau['fin']}"
                existing = EmploiDuTemps.objects.filter(
                    annee=emploi.annee,
                    trimestre=emploi.trimestre,
                    secteur=emploi.secteur,
                    jour=jour,
                    heure_debut=creneau['debut'],
                    heure_fin=creneau['fin']
                ).first()
                emplois_existants[jour][creneau_str] = existing

        return render(request, self.template_name, {
            'emploi': emploi,
            'creneaux': creneaux,
            'jours': jours,
            'matieres': matieres,
            'professeurs': professeurs,
            'salles': salles,
            'emplois_existants': emplois_existants,
        })


    def post(self, request, pk):
        emploi = get_object_or_404(EmploiDuTemps, pk=pk)

        try:
            data = request.POST
            annee_id = emploi.annee.id
            trimestre_id = emploi.trimestre.id
            secteur_id = emploi.secteur.id

            # D'abord supprimer les emplois existants pour ce secteur/année/trimestre
            EmploiDuTemps.objects.filter(
                annee_id=annee_id,
                trimestre_id=trimestre_id,
                secteur_id=secteur_id
            ).delete()

            # Jours de la semaine
            jours = ['Lundi', 'Mardi', 'Mercredi', 'Jeudi', 'Vendredi']

            # Sauvegarder les nouveaux emplois
            creneau_debuts = data.getlist('creneau_debut[]')
            creneau_fins = data.getlist('creneau_fin[]')

            for i in range(len(creneau_debuts)):
                debut = creneau_debuts[i]
                fin = creneau_fins[i]

                for jour in jours:
                    matiere_id = data.get(f'matiere_{jour}_{debut}_{fin}')
                    professeur_id = data.get(f'professeur_{jour}_{debut}_{fin}')
                    salle_id = data.get(f'salle_{jour}_{debut}_{fin}')

                    if matiere_id and professeur_id and salle_id:
                        EmploiDuTemps.objects.create(
                            annee_id=annee_id,
                            trimestre_id=trimestre_id,
                            secteur_id=secteur_id,
                            jour=jour,
                            heure_debut=debut,
                            heure_fin=fin,
                            matiere_id=matiere_id,
                            professeur_id=professeur_id,
                            salle_id=salle_id
                        )

            messages.success(request, _("L'emploi du temps a été mis à jour avec succès."))
            return redirect('emploi_liste')

        except Exception as e:
            messages.error(request, f"Une erreur est survenue: {str(e)}")
            return redirect('emploi_grille_edit', pk=pk)



def load_trimestres(request):
    annee_id = request.GET.get('annee_id')
    if not annee_id:
        return JsonResponse({'error': 'Paramètre annee_id manquant'}, status=400)

    trimestres = Trimestre.objects.filter(annee_id=annee_id).order_by('annee')
    data = [{'id': t.id, 'nom': t.numero_trimestre, 'nom_fr': t.nom} for t in trimestres]
    return JsonResponse(data, safe=False)

def emploi_par_secteur(request):
    annees = Annee.objects.all()
    trimestres = Trimestre.objects.none()  # Initialement vide
    secteurs = Secteur.objects.none()  # Initialement vide

    annee_id = request.GET.get('annee_id')
    trimestre_id = request.GET.get('trimestre_id')
    secteur_id = request.GET.get('secteur_id')

    emploi = None
    annee_selectionnee = None
    trimestre_selectionne = None
    secteur_selectionne = None

    # Si une année est sélectionnée, charger les trimestres correspondants
    if annee_id:
        annee_selectionnee = get_object_or_404(Annee, pk=annee_id)
        trimestres = Trimestre.objects.filter(annee=annee_selectionnee)

        # Si un trimestre est sélectionné, charger les secteurs
        if trimestre_id:
            trimestre_selectionne = get_object_or_404(Trimestre, pk=trimestre_id)
            secteurs = Secteur.objects.all()  # Ou appliquer un filtre si nécessaire

            # Si un secteur est sélectionné, charger l'emploi du temps
            if secteur_id:
                secteur_selectionne = get_object_or_404(Secteur, pk=secteur_id)
                filters = {
                    'secteur': secteur_selectionne,
                    'annee': annee_selectionnee,
                    'trimestre': trimestre_selectionne
                }
                emploi = EmploiDuTemps.objects.filter(**filters).order_by('jour', 'heure_debut')

    entete = Entete.objects.first()

    context = {
        'annees': annees,
        'trimestres': trimestres,
        'secteurs': secteurs,
        'emploi': emploi,
        'annee_selectionnee': annee_selectionnee,
        'trimestre_selectionne': trimestre_selectionne,
        'secteur_selectionne': secteur_selectionne,
        'entete': entete,
        'langue': get_language(),  # ajoute cette ligne

    }

    return render(request, 'emploi/emploi_par_secteur.html', context)