import logging
logger = logging.getLogger(__name__)
from django.utils.translation import gettext as _
# emploi/views.py
from django.contrib import messages
from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Q
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, render, redirect
from django.urls import reverse, reverse_lazy
from django.utils.translation import get_language
from django.views import View
from django.views.generic import ListView, CreateView, UpdateView, DeleteView

from annee.models import Annee
from branches.models import Secteur
from entete.models import Entete
from matiers.models import Matiere
from parametres.models import Parametres
from etudiant.models import Etudiant
from professeur.models import Professeur
from salle.models import Salle
from trimestre.models import Trimestre
from . import modifications
from .models import EmploiDuTemps, ModificationEmploi
from .forms import EmploiDuTempsForm, EmploiParametresForm
from django.core.exceptions import ValidationError
from django.db.models import Prefetch, Q


def _auteur(request):
    return str(request.user) if getattr(request.user, 'is_authenticated', False) else ''


def _message_portee(portee):
    if portee == ModificationEmploi.SEMAINE:
        return _("Modification enregistrée pour la semaine actuelle seulement : l'emploi du temps hebdomadaire n'a pas changé.")
    return _("Modification enregistrée pour la semaine actuelle et toutes les semaines suivantes.")


def _page_confirmation(request, changements, retour_url):
    """Demande la portée du changement (cette semaine seulement, ou aussi les suivantes) : la page renvoie
    les mêmes champs, plus `portee`."""
    champs = [(nom, valeurs) for nom, valeurs in request.POST.lists() if nom not in ('csrfmiddlewaretoken', 'portee')]
    return render(request, 'emploi/confirmer_portee.html', {
        'changements': modifications.decrire(changements),
        'champs': champs,
        'retour_url': retour_url,
        'portees': ModificationEmploi.PORTEES,
    })


def _creneau_du_formulaire(donnees):
    return modifications.creneau(
        donnees['jour'], donnees['heure_debut'], donnees['heure_fin'],
        donnees['matiere'].pk, donnees['professeur'].pk, donnees['salle'].pk)


def _classe_du_formulaire(donnees):
    return donnees['annee'].pk, donnees['trimestre'].pk, donnees['secteur'].pk

class EmploiListView(ListView):
    model = EmploiDuTemps
    template_name = 'emploi/list.html'
    context_object_name = 'secteurs_emplois'

    def get_queryset(self):
        # Récupérer tous les secteurs avec leurs emplois du temps (hors cours par niveau, listés à part)
        return Secteur.objects.prefetch_related(
            Prefetch('emploidutemps_set',
                    queryset=EmploiDuTemps.objects.filter(niveau__isnull=True)
                    .select_related('matiere', 'professeur', 'salle')
                    .order_by('jour', 'heure_debut')))

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['emplois_niveaux'] = (EmploiDuTemps.objects.filter(niveau__isnull=False)
                                      .select_related('matiere', 'professeur', 'salle', 'niveau', 'trimestre')
                                      .order_by('niveau__nom_fr', 'jour', 'heure_debut'))
        return context

class PorteeDuChangementMixin:
    """Ajout ou modification d'un créneau : si le changement touche une classe qui a déjà un emploi du temps, on
    demande s'il vaut pour cette semaine seulement ou aussi pour les semaines suivantes (voir modifications.py)."""

    def changement(self, form):
        """(avant, apres) du créneau, ou None si rien à confirmer (autre classe, première saisie, rien de changé)."""
        raise NotImplementedError

    def form_valid(self, form):
        try:
            couple = self.changement(form)
            if couple is None:
                return super().form_valid(form)
            portee = self.request.POST.get('portee')
            if portee not in modifications.PORTEES:
                return _page_confirmation(self.request, [couple], self.success_url)
            annee_id, trimestre_id, secteur_id = _classe_du_formulaire(form.cleaned_data)
            with transaction.atomic():
                if portee == ModificationEmploi.SUIVANTES:
                    reponse = super().form_valid(form)  # enregistre tout le formulaire (niveau, langue, etc.)
                else:
                    reponse = redirect(self.success_url)  # le modèle hebdomadaire reste tel quel (rien n'est enregistré)
                modifications.consigner([couple], annee_id=annee_id, trimestre_id=trimestre_id,
                                        secteur_id=secteur_id, portee=portee, par=_auteur(self.request))
            messages.success(self.request, _message_portee(portee))
            return reponse
        except ValidationError as e:
            form.add_error(None, e)
            return self.form_invalid(form)


class EmploiCreateView(PorteeDuChangementMixin, CreateView):
    model = EmploiDuTemps
    form_class = EmploiDuTempsForm
    template_name = 'emploi/form.html'
    success_url = reverse_lazy('emploi_liste')

    def changement(self, form):
        classe = _classe_du_formulaire(form.cleaned_data)
        if not modifications.etat_actuel(*classe):  # première saisie de la classe : aucun changement à confirmer
            return None
        return None, _creneau_du_formulaire(form.cleaned_data)


class EmploiUpdateView(PorteeDuChangementMixin, UpdateView):
    model = EmploiDuTemps
    form_class = EmploiDuTempsForm
    template_name = 'emploi/form.html'
    success_url = reverse_lazy('emploi_liste')

    def changement(self, form):
        enregistre = EmploiDuTemps._base_manager.get(pk=self.object.pk)  # l'instance du formulaire est déjà modifiée
        if (enregistre.annee_id, enregistre.trimestre_id, enregistre.secteur_id) != _classe_du_formulaire(form.cleaned_data):
            return None  # le cours change de classe : ce n'est pas un changement d'horaire
        avant, apres = modifications.creneau_de(enregistre), _creneau_du_formulaire(form.cleaned_data)
        if modifications.identiques(avant, apres):
            return None
        return avant, apres


class EmploiDeleteView(DeleteView):
    model = EmploiDuTemps
    template_name = 'emploi/delete_confirm.html'
    success_url = reverse_lazy('emploi_liste')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['portees'] = ModificationEmploi.PORTEES
        return context

    def form_valid(self, form):
        portee = self.request.POST.get('portee')
        if portee not in modifications.PORTEES:
            portee = ModificationEmploi.SUIVANTES
        avant = modifications.creneau_de(self.object)
        with transaction.atomic():
            modifications.consigner([(avant, None)], annee_id=self.object.annee_id,
                                    trimestre_id=self.object.trimestre_id, secteur_id=self.object.secteur_id,
                                    portee=portee, par=_auteur(self.request))
            if portee == ModificationEmploi.SUIVANTES:
                self.object.delete()
        messages.success(self.request, _message_portee(portee))
        return redirect(self.get_success_url())


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
    @staticmethod
    def _detail_conflit(jour, debut, fin, salle_id, professeur_id, secteur_id, annee_id, trimestre_id):
        """Décrit le cours déjà programmé qui bloque l'enregistrement (salle ou professeur occupé)."""
        autres = (EmploiDuTemps.objects.filter(jour=jour, annee_id=annee_id, trimestre_id=trimestre_id,
                                               heure_debut__lt=fin, heure_fin__gt=debut)
                  .exclude(secteur_id=secteur_id)
                  .filter(professeur_id=professeur_id)
                  .select_related('secteur', 'professeur', 'salle', 'matiere')[:2])
        return " ; ".join(
            _("%(classe)s — %(matiere)s, %(prof)s, salle %(salle)s (%(debut)s-%(fin)s)") % {
                'classe': a.secteur.nom, 'matiere': a.matiere.nom, 'prof': a.professeur,
                'salle': a.salle, 'debut': str(a.heure_debut)[:5], 'fin': str(a.heure_fin)[:5]}
            for a in autres)

    def post(self, request):
        secteur_id = request.POST.get('secteur_id', '')
        if not secteur_id.isdigit():
            return JsonResponse({'success': False, 'error': _("Classe introuvable.")}, status=400)
        parametres = Parametres.get_instance()
        classe = {'annee_id': parametres.annee_courante.id, 'trimestre_id': parametres.trimestre_courant.id,
                  'secteur_id': int(secteur_id)}
        try:
            return self._enregistrer(request, classe)
        except ValidationError as e:
            # tout est annulé : l'ancien emploi du temps reste intact
            texte = " ".join(e.messages)
            creneau = getattr(e, 'slot', None)
            if creneau:
                texte = _("%(jour)s %(debut)s-%(fin)s : %(erreur)s") % {
                    'jour': _(creneau['jour']), 'debut': f"{creneau['heure_debut']:%H:%M}",
                    'fin': f"{creneau['heure_fin']:%H:%M}", 'erreur': texte}
                detail = self._detail_conflit(
                    jour=creneau['jour'], debut=creneau['heure_debut'], fin=creneau['heure_fin'],
                    salle_id=creneau['salle_id'], professeur_id=creneau['professeur_id'], **classe)
                if detail:
                    texte += " " + _("Déjà occupé par : %(detail)s") % {'detail': detail}
            return JsonResponse({'success': False, 'error': texte}, status=400)
        except Exception:
            logger.exception("Erreur inattendue")
            return JsonResponse({'success': False, 'error': _("Une erreur est survenue. Veuillez réessayer ou contacter l'administration.")}, status=400)

    def _enregistrer(self, request, classe):
        portee = request.POST.get('portee')
        statut, changements = modifications.enregistrer_grille(
            modifications.grille_depuis_post(request.POST), portee=portee, par=_auteur(request), **classe)
        if statut == 'confirmer':
            # rien n'est enregistré : la page demande la portée (cette semaine seulement ou aussi les suivantes)
            return JsonResponse({'success': False, 'confirmation': True,
                                 'changements': modifications.decrire(changements)})
        message = _message_portee(portee) if statut == 'applique' else ''
        return JsonResponse({'success': True, 'message': str(message)})


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
        retour = reverse('emploi_grille_edit', args=[pk])
        try:
            data = request.POST
            portee = data.get('portee')
            statut, changements = modifications.enregistrer_grille(
                modifications.grille_depuis_post(data), annee_id=emploi.annee_id, trimestre_id=emploi.trimestre_id,
                secteur_id=emploi.secteur_id, portee=portee, par=_auteur(request))
            if statut == 'confirmer':
                # rien n'est enregistré : on demande la portée (cette semaine seulement ou aussi les suivantes)
                return _page_confirmation(request, changements, retour)
            if statut == 'applique':
                messages.success(request, _message_portee(portee))
            else:
                messages.success(request, _("L'emploi du temps a été mis à jour avec succès."))
            return redirect('emploi_liste')

        except ValidationError as e:
            messages.error(request, " ".join(e.messages))
            return redirect('emploi_grille_edit', pk=pk)
        except Exception:
            logger.exception("Erreur inattendue")
            messages.error(request, _("Une erreur est survenue. Veuillez réessayer ou contacter l'administration."))
            return redirect('emploi_grille_edit', pk=pk)



def load_trimestres(request):
    annee_id = request.GET.get('annee_id')
    if not annee_id:
        return JsonResponse({'error': _("Paramètre annee_id manquant")}, status=400)

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
                # cours du secteur + cours par niveau (langues) suivis par des élèves de ce secteur
                niveaux_du_secteur = list(Etudiant._base_manager.filter(
                    secteur=secteur_selectionne, annee=annee_selectionnee, niveau__isnull=False
                ).values_list('niveau_id', flat=True).distinct())
                emploi = (EmploiDuTemps.objects.filter(annee=annee_selectionnee, trimestre=trimestre_selectionne)
                          .filter(Q(secteur=secteur_selectionne, niveau__isnull=True) | Q(niveau_id__in=niveaux_du_secteur))
                          .select_related('matiere', 'professeur', 'salle', 'niveau')
                          .order_by('jour', 'heure_debut'))

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