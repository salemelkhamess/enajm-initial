import logging
logger = logging.getLogger(__name__)
from datetime import datetime

from django.db import transaction
from django.urls import reverse_lazy
from django.views.generic import ListView, CreateView, UpdateView, DeleteView
from annee.models import Annee
from branches.models import Secteur
from emploie.models import EmploiDuTemps
from matiers.models import Matiere
from parametres.models import Parametres
from parametres.utils import get_annee_courante, get_trimestre_courant
from trimestre.models import Trimestre
from .forms import PresenceEtudiantForm, PresenceFilterForm, PresenceForm, JustificationForm
from django.db.models import Count
from entete.models import Entete
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from etudiant.models import Etudiant
from niveaux.models import Niveau
from matiers.models import matieres_de_classe
from etudiant.noms import fusionner_noms
from .models import PresenceEtudiant, DocumentJustification, JustificationPeriode, q_comptee, q_en_attente
from django.http import HttpResponseForbidden, FileResponse, Http404
from django.core.exceptions import PermissionDenied
from django.views.generic import FormView, TemplateView
from django.urls import reverse
from django.http import JsonResponse
from django.utils.translation import gettext_lazy as _, get_language
from django.views.decorators.http import require_GET
from django.views.generic import View
from django.utils import timezone
from django.db.models import Count, Q, F
from django.http import JsonResponse
from django.views.decorators.cache import cache_control
from .models import PresenceEtudiant
from django.db.models import Count, F
import time
from django.db.models.functions import Cast
from django.db.models import DateTimeField

from django.utils.translation import gettext as _

class PresenceEtudiantListView(ListView):
    model = PresenceEtudiant
    template_name = 'presence_etudiant/list.html'
    context_object_name = 'presences'

class PresenceEtudiantCreateView(CreateView):
    model = PresenceEtudiant
    form_class = PresenceEtudiantForm
    template_name = 'presence_etudiant/create.html'
    success_url = reverse_lazy('presence_liste')

class PresenceEtudiantUpdateView(UpdateView):
    model = PresenceEtudiant
    form_class = PresenceEtudiantForm
    template_name = 'presence_etudiant/edit.html'
    success_url = reverse_lazy('presence_liste')

class PresenceEtudiantDeleteView(DeleteView):
    model = PresenceEtudiant
    template_name = 'presence_etudiant/delete.html'
    success_url = reverse_lazy('presence_liste')


from django.shortcuts import render
from django.utils.dateparse import parse_date
from .models import PresenceEtudiant


def rapport_absences(request):
    # Récupérer les paramètres par défaut
    parametres = Parametres.get_instance()

    date_debut = request.GET.get('date_debut')
    date_fin = request.GET.get('date_fin')
    annee_id = request.GET.get('annee_id', str(parametres.annee_courante.id))
    trimestre_id = request.GET.get('trimestre_id', str(parametres.trimestre_courant.id))
    secteur_id = request.GET.get('secteur_id')
    secteur = None

    # Filtrer les absences non justifiées
    absences = PresenceEtudiant.objects.filter(
        present=False,
        is_justified=False
    )

    # Filtres
    if date_debut and date_fin:
        try:
            date_debut_obj = parse_date(date_debut)
            date_fin_obj = parse_date(date_fin)
            if date_debut_obj and date_fin_obj:
                absences = absences.filter(date_cours__range=[date_debut_obj, date_fin_obj])
        except:
            pass

    if annee_id and annee_id != 'all':
        absences = absences.filter(annee_id=annee_id)

    if secteur_id and secteur_id != 'all':
        absences = absences.filter(etudiant__secteur_id=secteur_id)
        secteur = Secteur.objects.filter(id=secteur_id).first()

    if trimestre_id and trimestre_id != 'all':
        trimestre = Trimestre.objects.filter(id=trimestre_id).first()
        if trimestre:
            absences = absences.filter(date_cours__range=(trimestre.debut, trimestre.fin))

    # Group by sector, student and subject
    # Dans la vue rapport_absences
    resume_absences = absences.values(
        'etudiant__secteur__id',
        'etudiant__secteur__nom',
        'etudiant__id',
        'etudiant__nom',
        'etudiant__prenom',
        'etudiant__matricule',
        'matiere__nom',
        'jour',
        'date_cours'  # Ajout de la date du cours
    ).annotate(
        total_absences=Count('id'),
        en_attente=Count('id', filter=q_en_attente())
    ).order_by('etudiant__secteur__nom', 'etudiant__nom', 'matiere__nom')

    # Organize data by sector for template
    absences_par_secteur = {}
    for item in resume_absences:
        secteur_id = item['etudiant__secteur__id']
        etudiant_id = item['etudiant__id']

        if secteur_id not in absences_par_secteur:
            absences_par_secteur[secteur_id] = {
                'nom': item['etudiant__secteur__nom'],
                'etudiants': {}
            }

        if etudiant_id not in absences_par_secteur[secteur_id]['etudiants']:
            absences_par_secteur[secteur_id]['etudiants'][etudiant_id] = {
                'nom_complet': fusionner_noms(item['etudiant__prenom'], item['etudiant__nom']),
                'matricule': item['etudiant__matricule'],
                'absences': []
            }

        absences_par_secteur[secteur_id]['etudiants'][etudiant_id]['absences'].append({
            'matiere': item['matiere__nom'],
            'jour': _(item['jour']),
            'date_cours': item['date_cours'].strftime('%d/%m/%Y'),  # Formatage de la date
            # toutes les absences sont comptées ; celles qui n'ont pas encore dépassé 72 h sont seulement signalées
            'seances': item['total_absences'],
            'heures': item['total_absences'] * 2,
            'en_attente': item['en_attente'],
        })
    # Calculer le nombre total de lignes par secteur pour le rowspan
    for secteur_id, secteur_data in absences_par_secteur.items():
        total_lignes = 0
        for etudiant_id, etudiant_data in secteur_data['etudiants'].items():
            total_lignes += len(etudiant_data['absences'])
        secteur_data['total_lignes'] = total_lignes

    resume_etudiants = []
    for secteur_id, secteur_data in absences_par_secteur.items():
        for etudiant_id, etudiant_data in secteur_data['etudiants'].items():
            total_absences = sum(a['seances'] for a in etudiant_data['absences'])
            total_heures = sum(a['heures'] for a in etudiant_data['absences'])

            resume_etudiants.append({
                'secteur': secteur_data['nom'],
                'nom_complet': etudiant_data['nom_complet'],
                'matricule': etudiant_data['matricule'],
                'total_absences': total_absences,
                'total_heures': total_heures
            })

    resume_par_secteur = {}
    for secteur_id, secteur_data in absences_par_secteur.items():
        resume_par_secteur[secteur_id] = {
            'nom_secteur': secteur_data['nom'],
            'etudiants': [],
            'total_absences': 0,
            'total_heures': 0
        }

        for etudiant_id, etudiant_data in secteur_data['etudiants'].items():
            total_absences = sum(a['seances'] for a in etudiant_data['absences'])
            total_heures = sum(a['heures'] for a in etudiant_data['absences'])

            resume_par_secteur[secteur_id]['etudiants'].append({
                'nom_complet': etudiant_data['nom_complet'],
                'matricule': etudiant_data['matricule'],
                'total_absences': total_absences,
                'total_heures': total_heures
            })

            # Calcul des totaux du secteur
            resume_par_secteur[secteur_id]['total_absences'] += total_absences
            resume_par_secteur[secteur_id]['total_heures'] += total_heures



    context = {
        'absences_par_secteur': absences_par_secteur,
        'date_debut': date_debut,
        'date_fin': date_fin,
        'annees': Annee.objects.all(),
        'secteurs': Secteur.objects.all(),
        'trimestres': Trimestre.objects.all(),
        'annee_id': annee_id,
        'secteur_id': secteur_id,
        'trimestre_id': trimestre_id,
        'entete': Entete.objects.first(),
        'langue': get_language(),
        'secteur': secteur,
        'titre_rapport': _("Rapport des absences non justifiées par secteur"),
        'resume_etudiants': resume_etudiants,  # Ajout du résumé
        'resume_par_secteur': resume_par_secteur,  # Nouveau résumé groupé

    }

    return render(request, 'presence_etudiant/rapport_absences.html', context)

def rapport_absences_by_class(request):
    # Récupérer les paramètres courants
    parametres = Parametres.get_instance()
    annee_courante = parametres.annee_courante
    trimestre_courant = parametres.trimestre_courant

    # Récupérer les filtres du formulaire
    date_debut = request.GET.get('date_debut')
    date_fin = request.GET.get('date_fin')
    secteur_id = request.GET.get('secteur_id')

    # Filtrer uniquement les absences non justifiées
    absences = PresenceEtudiant.objects.filter(
        q_comptee(),
        annee=annee_courante,
        trimestre=trimestre_courant
    )

    # Appliquer les filtres supplémentaires
    if date_debut and date_fin:
        try:
            date_debut_obj = parse_date(date_debut)
            date_fin_obj = parse_date(date_fin)
            if date_debut_obj and date_fin_obj:
                absences = absences.filter(date_cours__range=[date_debut_obj, date_fin_obj])
        except:
            pass

    if secteur_id:
        absences = absences.filter(etudiant__secteur_id=secteur_id)

    # Grouper par secteur, étudiant et matière
    absences_par_etudiant = absences.values(
        'etudiant__secteur__nom',
        'etudiant__matricule',
        'etudiant__nom',
        'etudiant__prenom',
    ).annotate(
        nombre_absences=Count('id')
    ).order_by('etudiant__secteur__nom', 'etudiant__nom')

    context = {
        'absences_par_etudiant': absences_par_etudiant,
        'date_debut': date_debut,
        'date_fin': date_fin,
        'annee_courante': annee_courante,
        'trimestre_courant': trimestre_courant,
        'secteurs': Secteur.objects.all(),
        'secteur_id': secteur_id,
        'entete': Entete.objects.first(),
        'langue': get_language(),
        'titre_rapport': _("Rapport des absences non justifiées par étudiant"),
    }

    return render(request, 'presence_etudiant/rapport_absences_par_classe.html', context)

class PresenceSelectionView(FormView):
    template_name = 'presence_etudiant/selection.html'
    form_class = PresenceFilterForm

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['langue'] = get_language()  # ici on ajoute la langue dans le contexte
        return context

    def form_valid(self, form):
        # Stocker les paramètres en session pour la vue suivante
        self.request.session['presence_filter'] = {
            'annee_id': form.cleaned_data['annee'].id,
            'trimestre_id': form.cleaned_data['trimestre'].id,
            'secteur_id': form.cleaned_data['secteur'].id,
            'jour': form.cleaned_data['jour'],
            'date_cours': form.cleaned_data['date_cours'].strftime('%Y-%m-%d')
        }
        return redirect(reverse('presence_saisie'))

class PresenceSaisieView(TemplateView):
    template_name = 'presence_etudiant/saisie.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # Récupérer les données de la session si elles existent
        session_data = self.request.session.get('presence_data', {})
        post_data = session_data.get('post_data', {})

        filter_data = {
            'annee_id': self.request.GET.get('annee') or session_data.get('annee_id'),
            'trimestre_id': self.request.GET.get('trimestre') or session_data.get('trimestre_id'),
            'secteur_id': self.request.GET.get('secteur') or session_data.get('secteur_id'),
            'jour': self.request.GET.get('jour') or session_data.get('jour'),
            'date_cours': self.request.GET.get('date_cours') or session_data.get('date_cours')
        }

        # Récupération des étudiants du secteur
        etudiants = Etudiant.objects.filter(secteur_id=filter_data['secteur_id'])

        # Récupération des emplois du temps
        emplois = EmploiDuTemps.objects.filter(
            secteur_id=filter_data['secteur_id'],
            trimestre_id=filter_data['trimestre_id'],
            jour=filter_data['jour']
        ).order_by('heure_debut')

        # Récupérer les présences existantes pour pré-remplir le formulaire
        presences_existantes = {}
        justifications_existantes = {}
        if filter_data['date_cours']:
            presences = PresenceEtudiant.objects.filter(
                date_cours=filter_data['date_cours'],
                trimestre_id=filter_data['trimestre_id'],
                jour=filter_data['jour'],
                etudiant__secteur_id=filter_data['secteur_id']
            )
            for presence in presences:
                key = f'presence_{presence.etudiant.id}_{presence.matiere.id}'
                justification_key = f'justification_{presence.etudiant.id}_{presence.matiere.id}'
                # Convertir le booléen en 'present' ou 'absent'
                presences_existantes[key] = 'present' if presence.present else 'absent'
                justifications_existantes[justification_key] = presence.justification or ''
                print(f"Debug - {key}: {presence.present} -> {presences_existantes[key]}")  # Ligne de debug

        context.update({
            'etudiants': etudiants,
            'emplois': emplois,
            'filter_data': filter_data,
            'post_data': post_data,
            'presences_existantes': presences_existantes,
            'justifications_existantes': justifications_existantes,
            'secteur': Secteur.objects.get(id=filter_data['secteur_id']),
            'is_update': bool(presences_existantes)
        })
        return context

class EnregistrerPresenceView(View):
    def post(self, request, *args, **kwargs):
        # Stocker les données en session pour conservation en cas d'erreur
        request.session['presence_data'] = {
            'post_data': request.POST.dict(),
            'annee_id': request.POST.get('annee_id'),
            'trimestre_id': request.POST.get('trimestre_id'),
            'secteur_id': request.POST.get('secteur_id'),
            'jour': request.POST.get('jour'),
            'date_cours': request.POST.get('date_cours')
        }

        try:
            # Récupération des paramètres de base
            annee_id = request.POST.get('annee_id')
            trimestre_id = request.POST.get('trimestre_id')
            secteur_id = request.POST.get('secteur_id')
            jour = request.POST.get('jour')
            date_cours = request.POST.get('date_cours')
            is_update = request.POST.get('is_update') == 'true'

            # Validation des données requises
            if not all([annee_id, trimestre_id, secteur_id, jour, date_cours]):
                raise ValueError("Tous les champs obligatoires doivent être remplis")

            # Récupération des étudiants et emplois du temps
            etudiants = Etudiant.objects.filter(secteur_id=secteur_id)
            emplois = EmploiDuTemps.objects.filter(
                secteur_id=secteur_id,
                trimestre_id=trimestre_id,
                jour=jour
            )

            # Enregistrement transactionnel
            with transaction.atomic():
                for etudiant in etudiants:
                    for emploi in emplois:
                        presence_key = f'presence_{etudiant.id}_{emploi.matiere.id}'
                        justification_key = f'justification_{etudiant.id}_{emploi.matiere.id}'

                        if presence_key in request.POST:
                            present = request.POST[presence_key] == 'present'
                            justification = request.POST.get(justification_key, '')

                            # Mise à jour directe sans suppression préalable
                            PresenceEtudiant.objects.update_or_create(
                                etudiant=etudiant,
                                matiere=emploi.matiere,
                                date_cours=date_cours,
                                jour=jour,
                                defaults={
                                    'annee_id': annee_id,
                                    'trimestre_id': trimestre_id,
                                    'present': present,
                                    'justification': justification,
                                    'date_justification': timezone.now().date() if not present else None,
                                    'is_justified': bool(justification) if not present else False
                                }
                            )

            # Nettoyage de la session après succès
            if 'presence_data' in request.session:
                del request.session['presence_data']

            # Message différent selon création ou mise à jour
            if is_update:
                messages.success(request, _("Présences mises à jour avec succès!"))
            else:
                messages.success(request, _("Présences enregistrées avec succès!"))

            return redirect('presence_liste')

        except Exception as e:
            logger.exception("Erreur inattendue")
            messages.error(request, _("Une erreur est survenue. Veuillez réessayer ou contacter l'administration."))
            return redirect('presence_saisie')

@require_GET
def load_trimestres(request):
    annee_id = request.GET.get('annee_id')
    if not annee_id:
        return JsonResponse({'error': _("Paramètre manquant")}, status=400)

    try:
        trimestres = Trimestre.objects.filter(annee_id=annee_id).order_by('numero_trimestre')
        # Retourner le format attendu par le frontend
        return JsonResponse({
            'options': [{
                'id': t.id,
                'text': f"{t.nom} ({_('Trimestre')} {t.numero_trimestre})"
            } for t in trimestres]
        })
    except Exception as e:
        logger.exception("Erreur inattendue")
        return JsonResponse({'error': _("Une erreur est survenue. Veuillez réessayer ou contacter l'administration.")}, status=500)


from django.contrib import messages


class GestionPresenceView(FormView):
    template_name = 'presence_etudiant/selectionh.html'
    form_class = PresenceForm
    success_url = reverse_lazy('presence:enregistrer')  # Avec namespace

    def form_valid(self, form):
        try:
            print("Données du formulaire validées:", form.cleaned_data)

            # Préparer les données de session
            session_data = {
                'secteur_id': form.cleaned_data['secteur'].id,
                'matiere_id': form.cleaned_data['matiere'].id,
                'date_cours': form.cleaned_data['date_cours'].strftime('%Y-%m-%d'),
                'jour': form.cleaned_data['jour']
            }

            # Enregistrer en session
            self.request.session['presence_data'] = session_data
            self.request.session.modified = True

            print("Redirection vers:", self.get_success_url())
            return super().form_valid(form)

        except Exception as e:
            print("ERREUR:", str(e))
            messages.error(self.request, _("Une erreur est survenue"))
            return self.form_invalid(form)

class EnregistrerPresenceViewH(TemplateView):
    template_name = 'presence_etudiant/enregistrement.html'


    def get(self, request, *args, **kwargs):
        # Debug: Affiche les données de session
        print("Session dans GET:", dict(request.session))
        return super().get(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        session_data = self.request.session.get('presence_data')

        if not session_data:
            print("ICI")
            messages.error(self.request, "Veuillez d'abord sélectionner les informations requises")
            return context

        try:
            secteur = Secteur.objects.get(id=session_data['secteur_id'])
            matiere = Matiere.objects.get(id=session_data['matiere_id'])
            etudiants = Etudiant.objects.filter(secteur=secteur)

            presences = []
            for etudiant in etudiants:
                presence, created = PresenceEtudiant.objects.get_or_create(
                    etudiant=etudiant,
                    matiere=matiere,
                    date_cours=session_data['date_cours'],
                    defaults={
                        'jour': session_data['jour'],
                        'present': True
                    }
                )
                presences.append(presence)

            context.update({
                'secteur': secteur,
                'matiere': matiere,
                'date_cours': session_data['date_cours'],
                'jour': session_data['jour'],
                'etudiants': etudiants,
                'presences': presences
            })

        except Exception as e:
            logger.exception("Erreur inattendue")
            messages.error(self.request, _("Une erreur est survenue. Veuillez réessayer ou contacter l'administration."))
            print("Erreur dans get_context_data:", str(e))  # Debug

        return context

    def post(self, request, *args, **kwargs):
        print("Données POST reçues:", request.POST)  # Debug
        session_data = request.session.get('presence_data')

        if not session_data:
            messages.error(request, _("Session expirée, veuillez recommencer"))
            return redirect('presence:selection')

        try:
            secteur = Secteur.objects.get(id=session_data['secteur_id'])
            matiere = Matiere.objects.get(id=session_data['matiere_id'])
            etudiants = Etudiant.objects.filter(secteur=secteur)

            for etudiant in etudiants:
                present = request.POST.get(f'present_{etudiant.id}', 'off') == 'on'
                justification = request.POST.get(f'justification_{etudiant.id}', '')

                PresenceEtudiant.objects.update_or_create(
                    etudiant=etudiant,
                    matiere=matiere,
                    date_cours=session_data['date_cours'],
                    defaults={
                        'present': present,
                        'justification': justification,
                        'jour': session_data['jour']
                    }
                )

            messages.success(request, _("Présences enregistrées avec succès!"))
            return redirect('presence:selection')

        except Exception as e:
            logger.exception("Erreur inattendue")
            messages.error(request, _("Une erreur est survenue. Veuillez réessayer ou contacter l'administration."))
            print("Erreur dans POST:", str(e))  # Debug
            return self.get(request, *args, **kwargs)

def charger_matieres(request):
    secteur_id = request.GET.get('secteur_id')
    matieres = matieres_de_classe(secteur_id)
    return JsonResponse([{'id': m.id, 'nom': m.nom} for m in matieres], safe=False)

def load_matieres(request):
    secteur_id = request.GET.get('secteur_id')
    matieres = matieres_de_classe(secteur_id)
    return JsonResponse([{'id': m.id, 'nom': m.nom} for m in matieres], safe=False)


class EnregistrementPresenceView(FormView):
    template_name = 'presence_etudiant/enregistrement.html'
    form_class = PresenceForm  # Assurez-vous que cette classe est importée

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['a_niveaux'] = Niveau.actifs().exists()   # le choix « niveau » n'apparaît que si des niveaux existent
        return context

    def form_valid(self, form):
        try:
            self.request.session['presence_data'] = {
                'secteur_id': form.cleaned_data['secteur'].id,
                'matiere_id': form.cleaned_data['matiere'].id,
                'date_cours': form.cleaned_data['date_cours'].isoformat(),
                'jour': form.cleaned_data['jour'],
                'niveau_id': form.cleaned_data['niveau'].id if form.cleaned_data.get('niveau') else None,
                'groupe_id': form.cleaned_data['groupe_obj'].id if form.cleaned_data.get('groupe_obj') else None,
            }
            self.request.session.modified = True

            return redirect('enregistrement_presence_etudiants')

        except KeyError as e:
            print(f"Erreur dans les données du formulaire: {e}")
            return self.form_invalid(form)


class EnregistrementPresenceEtudiantsView(TemplateView):
    template_name = 'presence_etudiant/enregistrement_etudiants.html'

    def get(self, request, *args, **kwargs):
        print("Getting session data:", request.session.get('presence_data'))
        if 'presence_data' not in request.session:
            messages.error(request, "Veuillez d'abord sélectionner un secteur, une matière et une date")
            return redirect('enregistrement_presence')
        return super().get(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        print("Données POST reçues:", request.POST)
        presence_data = request.session.get('presence_data')

        if not presence_data:
            messages.error(request, _("Session expirée, veuillez recommencer"))
            return redirect('enregistrement_presence')

        try:
            parametres = Parametres.get_instance()

            # Traiter chaque étudiant
            for key, value in request.POST.items():
                if key.startswith('etudiant_'):
                    etudiant_id = key.replace('etudiant_', '')
                    present = value == 'present'

                    PresenceEtudiant.objects.update_or_create(
                        etudiant_id=etudiant_id,
                        matiere_id=presence_data['matiere_id'],
                        date_cours=presence_data['date_cours'],
                        jour=presence_data['jour'],
                        trimestre=parametres.trimestre_courant,
                        defaults={
                            'present': present,
                            'annee': parametres.annee_courante,
                        }
                    )

            messages.success(request, _("Présences enregistrées avec succès!"))
            return redirect('enregistrement_presence')

        except Exception as e:
            logger.exception("Erreur inattendue")
            messages.error(request, _("Une erreur est survenue. Veuillez réessayer ou contacter l'administration."))
            print("Erreur:", str(e))
            return self.get(request, *args, **kwargs)
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        presence_data = self.request.session.get('presence_data')

        try:
            secteur_id = presence_data['secteur_id']
            matiere_id = presence_data['matiere_id']
            date_cours = presence_data['date_cours']
            jour = presence_data['jour']

            parametres = Parametres.get_instance()

            # Récupérer les étudiants : un niveau (cours de langue) ou tout un secteur
            niveau_id = presence_data.get('niveau_id')
            groupe_id = presence_data.get('groupe_id')
            if groupe_id:      # appel d'un groupe : seuls les élèves du groupe
                filtre_etudiants = {'affectations__groupe_id': groupe_id}
            else:
                filtre_etudiants = {'niveau_id': niveau_id} if niveau_id else {'secteur_id': secteur_id}
            from etudiant.models import ordre_matricule_croissant
            from groupes.models import Groupe
            etudiants = (Etudiant.objects.filter(annee=parametres.annee_courante, **filtre_etudiants)
                         .order_by(*ordre_matricule_croissant()))

            # Récupérer les présences existantes
            presences = PresenceEtudiant.objects.filter(
                etudiant__in=etudiants,
                matiere_id=matiere_id,
                date_cours=date_cours,
                jour=jour,
                trimestre=parametres.trimestre_courant
            )

            # Préparer la liste des étudiants avec leur statut
            etudiants_list = []
            presences_par_etudiant = {}
            for pr in presences.order_by('-id'):
                presences_par_etudiant[pr.etudiant_id] = pr   # une requête au lieu d'une par élève
            for etudiant in etudiants:
                presence = presences_par_etudiant.get(etudiant.id)
                etudiants_list.append({
                    'etudiant': etudiant,
                    'present': presence.present if presence else True,
                    'presence_id': presence.id if presence else None,
                })

            context.update({
                'etudiants': etudiants_list,
                'matiere': Matiere.objects.get(id=matiere_id),
                'groupe': Groupe.objects.filter(pk=groupe_id).first() if groupe_id else None,
                'date_cours': date_cours,
                'jour': jour,
                'annee_courante': parametres.annee_courante,
                'trimestre_courant': parametres.trimestre_courant,
            })

        except KeyError as e:
            print(f"Key error in session data: {e}")
            return redirect('enregistrement_presence')

        return context


def matieres_api(request):
    secteur_id = request.GET.get('secteur_id')
    if secteur_id:
        matieres = matieres_de_classe(secteur_id).values('id', 'nom')
        return JsonResponse(list(matieres), safe=False)
    return JsonResponse([], safe=False)



def liste_absences_non_justifiees(request):
    absences = PresenceEtudiant.objects.filter(
        present=False,
        is_justified=False
    ).select_related(
        'etudiant',
        'matiere',
        'trimestre',
        'annee'
    ).prefetch_related('documents').select_related('justif_periode')

    periodes = (JustificationPeriode.objects.filter(etat='soumise')
                .select_related('etudiant', 'soumise_par').prefetch_related('documents', 'absences'))
    return render(request, 'etudiants/liste_absence.html', {'absences': absences, 'periodes': periodes})


ROLES_DECISION = ('ADMIN', 'POINTEUR', 'SUPER_ADMIN')
EXTENSIONS_JUSTIFICATIF = ('.pdf', '.jpg', '.jpeg', '.png')
TAILLE_MAX_JUSTIFICATIF = 5 * 1024 * 1024
NB_MAX_DOCUMENTS = 5


def _peut_decider(user):
    return user.is_authenticated and any(user.has_role(r) for r in ROLES_DECISION)


def _peut_justifier(user):
    return user.is_authenticated and user.has_role('DOCTOR')


def valider_absence(request, absence_id):
    """Validation immédiate d'une absence (sans attendre les 72 h) : administration / pointeur / super admin."""
    absence = get_object_or_404(PresenceEtudiant, id=absence_id)
    if not _peut_decider(request.user):
        raise PermissionDenied
    if absence.etat_absence == 'justification_soumise':
        messages.warning(request, _("Une justification est en attente de décision : examinez-la d'abord."))
        return redirect('examiner_justification', absence_id=absence.id)

    if request.method == 'POST':
        absence.valider_maintenant()  # validation sans attendre les 72 h
        messages.success(request, _("L'absence a été validée avec succès."))
        return redirect('liste_absences_non_justifiees')

    return render(request, 'etudiants/confirmation_validation.html', {'absence': absence})


def modifier_statut_absence(request, absence_id):
    """
    Justification d'une absence par le médecin (avec pièces jointes éventuelles).
    Possible tant que l'absence n'est pas validée ; la justification doit ensuite être acceptée
    par l'administration, le pointeur ou le super administrateur.
    """
    absence = get_object_or_404(PresenceEtudiant.objects.select_related('etudiant', 'matiere'), pk=absence_id)
    if not _peut_justifier(request.user):
        raise PermissionDenied
    if absence.justif_periode_id and absence.justif_etat == 'soumise':
        messages.info(request, _("Cette absence fait partie d'une justification par période : modifiez-la depuis « Justifier par période »."))
        return redirect('justification_periode')
    if absence.present or not absence.justifiable:
        if absence.etat_absence == 'validee':
            messages.error(request, _("Cette absence est validée : elle ne peut plus être justifiée."))
        else:
            messages.error(request, _("Cette absence ne peut pas être justifiée."))
        return redirect('liste_absences_non_justifiees')

    erreurs = []
    if request.method == 'POST':
        texte = (request.POST.get('justification') or '').strip()
        date_just = parse_date(request.POST.get('date_justification') or '') or timezone.now().date()
        fichiers = request.FILES.getlist('documents')
        if not texte:
            erreurs.append(_("La justification est obligatoire."))
        if absence.documents.count() + len(fichiers) > NB_MAX_DOCUMENTS:
            erreurs.append(_("%(n)s documents maximum par absence.") % {'n': NB_MAX_DOCUMENTS})
        for f in fichiers:
            if not f.name.lower().endswith(EXTENSIONS_JUSTIFICATIF):
                erreurs.append(_("« %(nom)s » : formats acceptés : PDF, JPG, PNG.") % {'nom': f.name})
            elif f.size > TAILLE_MAX_JUSTIFICATIF:
                erreurs.append(_("« %(nom)s » dépasse 5 Mo.") % {'nom': f.name})
        if not erreurs:
            absence.justification = texte
            absence.date_justification = date_just
            absence.justif_etat = 'soumise'
            absence.justif_soumise_par = request.user
            absence.justif_soumise_le = timezone.now()
            absence.justif_motif_refus = None
            absence.save()
            for f in fichiers:
                DocumentJustification.objects.create(absence=absence, fichier=f, nom=f.name, ajoute_par=request.user)
            messages.success(request, _("Justification envoyée : elle doit être validée par l'administration."))
            # élève suivant : prochaine absence en attente d'un AUTRE élève dans la liste
            suivante = next((a for a in PresenceEtudiant.objects.filter(
                present=False, is_justified=False, id__gt=absence.id).exclude(etudiant_id=absence.etudiant_id)
                .select_related('etudiant').order_by('id') if a.etat_absence == 'en_attente'), None)
            if suivante:
                return redirect('modifier_statut_absence', absence_id=suivante.id)
            messages.info(request, _("Il n'y a plus d'élève à justifier dans la liste."))
            return redirect('liste_absences_non_justifiees')

    return render(request, 'etudiants/modifier.html', {
        'absence': absence, 'erreurs': erreurs,
        'texte': request.POST.get('justification', absence.justification or ''),
        'date_justification': request.POST.get('date_justification') or (absence.date_justification or timezone.now().date()).strftime('%Y-%m-%d'),
        'documents': absence.documents.all(), 'nb_max': NB_MAX_DOCUMENTS,
    })


def examiner_justification(request, absence_id):
    """Accepter ou refuser la justification déposée par le médecin (administration / pointeur / super admin)."""
    absence = get_object_or_404(PresenceEtudiant.objects.select_related('etudiant', 'matiere', 'justif_soumise_par'),
                                pk=absence_id)
    if not _peut_decider(request.user):
        raise PermissionDenied
    if absence.justif_periode_id and absence.justif_etat == 'soumise':
        return redirect('examiner_periode', periode_id=absence.justif_periode_id)
    if absence.etat_absence != 'justification_soumise':
        messages.info(request, _("Aucune justification en attente de décision pour cette absence."))
        return redirect('liste_absences_non_justifiees')

    propre = absence.justif_soumise_par_id == request.user.id
    if request.method == 'POST':
        if propre:
            messages.error(request, _("Vous ne pouvez pas valider une justification que vous avez vous-même déposée."))
            return redirect('examiner_justification', absence_id=absence.id)
        decision = request.POST.get('decision')
        if decision == 'accepter':
            absence.is_justified = True
            absence.status = True
            absence.justif_etat = 'acceptee'
            messages.success(request, _("Justification acceptée : l'absence est justifiée."))
        elif decision == 'refuser':
            motif = (request.POST.get('motif') or '').strip()
            if not motif:
                messages.error(request, _("Indiquez le motif du refus."))
                return redirect('examiner_justification', absence_id=absence.id)
            absence.is_justified = False
            absence.justif_etat = 'refusee'
            absence.justif_motif_refus = motif
            messages.success(request, _("Justification refusée."))
        else:
            return redirect('examiner_justification', absence_id=absence.id)
        absence.justif_decidee_par = request.user
        absence.justif_decidee_le = timezone.now()
        absence.save()
        return redirect('liste_absences_non_justifiees')

    return render(request, 'etudiants/examiner_justification.html', {
        'absence': absence, 'documents': absence.documents.all(), 'propre': propre})


def justificatif_document(request, document_id):
    """Téléchargement d'un justificatif : réservé au médecin et à l'administration (jamais en accès public)."""
    if not (_peut_justifier(request.user) or _peut_decider(request.user)):
        raise PermissionDenied
    doc = get_object_or_404(DocumentJustification, pk=document_id)
    try:
        fichier = doc.fichier.open('rb')
    except FileNotFoundError:
        raise Http404
    reponse = FileResponse(fichier, as_attachment=False, filename=doc.nom)
    reponse['X-Content-Type-Options'] = 'nosniff'
    return reponse


def absences_non_justifiees(request):
    # Récupérer les paramètres courants
    params = Parametres.get_instance()
    annee_courante = params.annee_courante
    trimestre_courant = params.trimestre_courant

    # Valeur par défaut: 12h
    hours = request.GET.get('hours', 12)

    try:
        hours = int(hours)
    except ValueError:
        hours = 12

    # Calculer le nombre de séances (1 séance = 2h)
    sessions_count = hours // 2

    # Récupérer les absences groupées par secteur et étudiant
    absences = PresenceEtudiant.objects.filter(
        q_comptee(),
        annee=annee_courante,  # Filtre par année courante
        trimestre=trimestre_courant  # Filtre par trimestre courant
    ).values(
        'etudiant__secteur__id',
        'etudiant__secteur__nom',
        'etudiant__id',
        'etudiant__matricule',
        'etudiant__nom',
        'etudiant__prenom'
    ).annotate(
        nombre_absences=Count('id'),
        nombre_heures=F('nombre_absences') * 2
    ).filter(
        nombre_heures__gte=hours
    ).order_by(
        'etudiant__secteur__nom',
        'etudiant__nom',
        'etudiant__prenom'
    )

    context = {
        'hours': hours,
        'absences_par_etudiant': absences,
        'annee_courante': annee_courante,
        'trimestre_courant': trimestre_courant,
        'entete': Entete.objects.filter(id=1)
    }

    return render(request, 'presence_etudiant/absences_non_justifiees.html', context)




@cache_control(no_cache=True, must_revalidate=True, no_store=True)
def check_absence_alerts(request):
    if not Parametres.get_real_instance().alertes_absences_actives:
        return JsonResponse({'alert': False})

    alert_threshold_hours = 12  # 12 heures comme seuil
    check_interval = 30  # Synchronisé avec le client (30s)

    last_check = request.session.get('last_absence_check', 0)
    current_time = time.time()

    if current_time - last_check < check_interval:
        return JsonResponse({'alert': False})

    # Requête simplifiée
    critical_students = PresenceEtudiant.objects.filter(
        q_comptee(),
        annee=get_annee_courante()
    ).values(
        'etudiant__id',
        'etudiant__nom',
        'etudiant__prenom'
    ).annotate(
        total_hours=Count('id') * 2  # 2h par absence
    ).filter(
        total_hours__gte=alert_threshold_hours
    )

    request.session['last_absence_check'] = current_time

    if critical_students.exists():
        students_list = [
            f"{fusionner_noms(s['etudiant__prenom'], s['etudiant__nom'])} ({s['total_hours']}h)"
            for s in critical_students
        ]
        return JsonResponse({
            'alert': True,
            'students': students_list,
            'message': _("Alerte ! %(count)s étudiants avec +%(hours)sh d'absences") % {
                'count': len(students_list),
                'hours': alert_threshold_hours
            }
        })

    return JsonResponse({'alert': False})

class AbsenceParMatiereView(ListView):
    template_name = 'presence_etudiant/absence_par_matiere.html'
    context_object_name = 'absences'
    model = PresenceEtudiant

    def get_queryset(self):
        # Récupérer les paramètres courants
        params = Parametres.get_instance()

        # Récupérer les paramètres du formulaire
        matiere_id = self.request.GET.get('matiere')
        date_debut = self.request.GET.get('date_debut')
        date_fin = self.request.GET.get('date_fin')

        # Filtrer les absences
        queryset = PresenceEtudiant.objects.filter(
            annee=params.annee_courante,
            trimestre=params.trimestre_courant,
            present=False,
            is_justified=False
        )

        if matiere_id:
            queryset = queryset.filter(matiere_id=matiere_id)

        if date_debut and date_fin:
            queryset = queryset.filter(
                date_cours__gte=date_debut,
                date_cours__lte=date_fin
            )

        return queryset.select_related('etudiant', 'matiere').order_by('date_cours', 'etudiant__nom')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['matieres'] = Matiere.objects.all()
        context['entete'] = Entete.objects.filter(id=1)
        context['total_seances_validees'] = sum(1 for a in context['absences'] if a.etat_absence == 'validee')
        return context


# --- Justification par période (autorisation de plusieurs jours) ----------------------------------------------
def _dates_periode(request):
    """(début, fin, erreur) lues dans l'adresse ou le formulaire ; par défaut aujourd'hui."""
    aujourdhui = timezone.now().date()
    debut = parse_date(request.POST.get('date_debut') or request.GET.get('date_debut') or '') or aujourdhui
    fin = parse_date(request.POST.get('date_fin') or request.GET.get('date_fin') or '') or debut
    if fin < debut:
        return debut, debut, _("La date de fin est antérieure à la date de début.")
    if (fin - debut).days > 90:
        return debut, fin, _("La période ne peut pas dépasser 90 jours.")
    return debut, fin, None


def _file_attente(debut=None, fin=None):
    """
    Élèves ayant des absences encore en attente (donc justifiables), du plus petit au plus grand matricule
    (éventuellement limitées à une période) : [{'etudiant': Etudiant, 'absences': [PresenceEtudiant, ...]}].
    """
    absences = (PresenceEtudiant.objects.filter(present=False, is_justified=False)
                .select_related('etudiant__secteur', 'matiere').order_by('date_cours'))
    if debut and fin:
        absences = absences.filter(date_cours__range=(debut, fin))
    groupes = {}
    for a in absences:
        if a.etat_absence == 'en_attente':
            groupes.setdefault(a.etudiant_id, {'etudiant': a.etudiant, 'absences': []})['absences'].append(a)
    for g in groupes.values():
        dates = [a.date_cours for a in g['absences'] if a.date_cours]
        g['du'], g['au'] = (min(dates), max(dates)) if dates else (None, None)
    return sorted(groupes.values(), key=lambda g: (len(g['etudiant'].matricule), g['etudiant'].matricule))


def justification_periode(request):
    """
    Le médecin justifie toutes les absences d'un élève sur une période (ex. du 11/11 au 13/11) avec un seul dossier
    (texte + documents). Après l'enregistrement, l'élève suivant de la liste s'affiche pour lui joindre son document.
    """
    from etudiant.models import Etudiant
    if not _peut_justifier(request.user):
        raise PermissionDenied
    debut, fin, erreur_periode = _dates_periode(request)
    erreurs = [erreur_periode] if erreur_periode else []
    # la liste montre tous les élèves ayant des absences encore justifiables ; la période se choisit pour chaque élève
    file = _file_attente()
    ids_file = [g['etudiant'].id for g in file]

    brut = request.POST.get('etudiant') or request.GET.get('etudiant')
    selection = Etudiant.objects.select_related('secteur').filter(pk=int(brut)).first() if brut and brut.isdigit() else None
    periode_choisie = bool(request.POST.get('date_debut') or request.GET.get('date_debut'))
    if selection and not periode_choisie:
        # période proposée par défaut : de la première à la dernière absence encore justifiable de l'élève
        dates = [a.date_cours for g in file if g['etudiant'].id == selection.id for a in g['absences'] if a.date_cours]
        if dates:
            debut, fin = min(dates), max(dates)

    if request.method == 'POST' and selection and not erreur_periode:
        texte = (request.POST.get('justification') or '').strip()
        fichiers = request.FILES.getlist('documents')
        if not texte:
            erreurs.append(_("La justification est obligatoire."))
        if len(fichiers) > NB_MAX_DOCUMENTS:
            erreurs.append(_("%(n)s documents maximum par absence.") % {'n': NB_MAX_DOCUMENTS})
        for f in fichiers:
            if not f.name.lower().endswith(EXTENSIONS_JUSTIFICATIF):
                erreurs.append(_("« %(nom)s » : formats acceptés : PDF, JPG, PNG.") % {'nom': f.name})
            elif f.size > TAILLE_MAX_JUSTIFICATIF:
                erreurs.append(_("« %(nom)s » dépasse 5 Mo.") % {'nom': f.name})
        if not erreurs:
            from django.db import transaction
            with transaction.atomic():
                periode = JustificationPeriode.objects.filter(etudiant=selection, date_debut=debut, date_fin=fin,
                                                              etat='soumise').first()
                if periode is None:
                    periode = JustificationPeriode(etudiant=selection, date_debut=debut, date_fin=fin)
                periode.justification, periode.etat = texte, 'soumise'
                periode.soumise_par, periode.soumise_le = request.user, timezone.now()
                periode.motif_refus = None
                periode.save()
                for f in fichiers:
                    DocumentJustification.objects.create(periode=periode, fichier=f, nom=f.name, ajoute_par=request.user)
                nb = 0
                for a in PresenceEtudiant.objects.filter(etudiant=selection, present=False, is_justified=False,
                                                         date_cours__range=(debut, fin)):
                    if a.etat_absence == 'en_attente':
                        a.justif_periode, a.justification, a.date_justification = periode, texte, timezone.now().date()
                        a.justif_etat, a.justif_soumise_par, a.justif_soumise_le = 'soumise', request.user, timezone.now()
                        a.justif_motif_refus = None
                        a.save()
                        nb += 1
            messages.success(request, _("Justification enregistrée pour %(nom)s (%(n)s absence(s)) : elle doit être validée par l'administration.")
                             % {'nom': selection.nom_prenom, 'n': nb})
            # élève suivant : celui qui vient après dans la liste, sinon le premier restant
            apres = _file_attente()
            ids_apres = [g['etudiant'].id for g in apres if g['etudiant'].id != selection.id]
            position = ids_file.index(selection.id) if selection.id in ids_file else -1
            suivant = next((i for i in ids_file[position + 1:] if i in ids_apres), ids_apres[0] if ids_apres else None)
            if suivant:
                return redirect(f"{request.path}?etudiant={suivant}")
            messages.info(request, _("Tous les élèves de cette période ont une justification."))
            return redirect('liste_absences_non_justifiees')

    # lien « passer à l'élève suivant » sans enregistrer
    suivant_sans_enregistrer = None
    if selection and selection.id in ids_file:
        reste = ids_file[ids_file.index(selection.id) + 1:]
        suivant_sans_enregistrer = reste[0] if reste else None
    absences_selection = [a for g in file if selection and g['etudiant'].id == selection.id
                          for a in g['absences'] if debut <= a.date_cours <= fin]
    existante = (JustificationPeriode.objects.filter(etudiant=selection, date_debut=debut, date_fin=fin, etat='soumise').first()
                 if selection else None)
    return render(request, 'etudiants/justification_periode.html', {
        'debut': debut, 'fin': fin, 'erreurs': erreurs, 'file': file, 'selection': selection,
        'absences_selection': absences_selection, 'suivant': suivant_sans_enregistrer, 'existante': existante,
        'tous_etudiants': Etudiant.objects.select_related('secteur').order_by('nom', 'prenom'),
        'texte': request.POST.get('justification') or request.GET.get('texte') or (existante.justification if existante else ''),
        'position': (ids_file.index(selection.id) + 1) if selection and selection.id in ids_file else None,
        'total_file': len(file), 'nb_max': NB_MAX_DOCUMENTS,
    })


def examiner_periode(request, periode_id):
    """Accepter ou refuser une justification par période : toutes les absences concernées sont décidées ensemble."""
    periode = get_object_or_404(JustificationPeriode.objects.select_related('etudiant__secteur', 'soumise_par'), pk=periode_id)
    if not _peut_decider(request.user):
        raise PermissionDenied
    if periode.etat != 'soumise':
        messages.info(request, _("Aucune justification en attente de décision pour cette absence."))
        return redirect('liste_absences_non_justifiees')
    propre = periode.soumise_par_id == request.user.id
    if request.method == 'POST':
        if propre:
            messages.error(request, _("Vous ne pouvez pas valider une justification que vous avez vous-même déposée."))
            return redirect('examiner_periode', periode_id=periode.id)
        decision = request.POST.get('decision')
        motif = (request.POST.get('motif') or '').strip()
        if decision == 'refuser' and not motif:
            messages.error(request, _("Indiquez le motif du refus."))
            return redirect('examiner_periode', periode_id=periode.id)
        if decision not in ('accepter', 'refuser'):
            return redirect('examiner_periode', periode_id=periode.id)
        from django.db import transaction
        maintenant = timezone.now()
        with transaction.atomic():
            periode.etat = 'acceptee' if decision == 'accepter' else 'refusee'
            periode.decidee_par, periode.decidee_le = request.user, maintenant
            periode.motif_refus = motif if decision == 'refuser' else None
            periode.save()
            for a in periode.absences.filter(is_justified=False, justif_etat='soumise'):
                if decision == 'accepter':
                    a.is_justified, a.status, a.justif_etat = True, True, 'acceptee'
                else:
                    a.justif_etat, a.justif_motif_refus = 'refusee', motif
                a.justif_decidee_par, a.justif_decidee_le = request.user, maintenant
                a.save()
        messages.success(request, _("Justification acceptée : l'absence est justifiée.") if decision == 'accepter'
                         else _("Justification refusée."))
        return redirect('liste_absences_non_justifiees')
    return render(request, 'etudiants/examiner_periode.html', {
        'periode': periode, 'documents': periode.documents.all(),
        'absences': periode.absences.select_related('matiere').order_by('date_cours'), 'propre': propre})



def _evenements_justification(periodes, individuelles, user):
    """Fusionne les justifications par période et les justifications d'absences isolées, du plus récent au plus ancien."""
    evenements = []
    for p in periodes:
        evenements.append({
            'genre': 'periode', 'etudiant': p.etudiant, 'date': p.soumise_le, 'etat': p.etat, 'texte': p.justification,
            'debut': p.date_debut, 'fin': p.date_fin, 'jours': p.nb_jours,
            'absences': list(p.absences.all()), 'documents': list(p.documents.all()),
            'par': p.soumise_par, 'decide_par': p.decidee_par, 'decide_le': p.decidee_le, 'motif': p.motif_refus,
            'lien_examen': p.etat == 'soumise' and _peut_decider(user), 'periode_id': p.id})
    for a in individuelles:
        evenements.append({
            'genre': 'absence', 'etudiant': a.etudiant, 'date': a.justif_soumise_le, 'etat': a.justif_etat,
            'texte': a.justification, 'debut': a.date_cours, 'fin': a.date_cours, 'jours': 1, 'absences': [a],
            'documents': list(a.documents.all()), 'par': a.justif_soumise_par, 'decide_par': a.justif_decidee_par,
            'decide_le': a.justif_decidee_le, 'motif': a.justif_motif_refus,
            'lien_examen': a.justif_etat == 'soumise' and _peut_decider(user), 'absence_id': a.id})
    evenements.sort(key=lambda e: e['date'] or timezone.now(), reverse=True)
    return evenements


def _requetes_historique(etudiant=None):
    periodes = (JustificationPeriode.objects.select_related('etudiant__secteur', 'soumise_par', 'decidee_par')
                .prefetch_related('documents', 'absences__matiere'))
    individuelles = (PresenceEtudiant.objects.filter(present=False, justif_periode__isnull=True)
                     .exclude(justif_etat='aucune')
                     .select_related('etudiant__secteur', 'matiere', 'justif_soumise_par', 'justif_decidee_par')
                     .prefetch_related('documents'))
    if etudiant is not None:
        periodes = periodes.filter(etudiant=etudiant)
        individuelles = individuelles.filter(etudiant=etudiant)
    return periodes, individuelles


def historique_justifications(request, etudiant_id):
    """Historique complet des justifications d'un élève : périodes et absences justifiées une à une."""
    from etudiant.models import Etudiant
    if not (_peut_justifier(request.user) or _peut_decider(request.user)):
        raise PermissionDenied
    etudiant = get_object_or_404(Etudiant.objects.select_related('secteur'), pk=etudiant_id)
    periodes, individuelles = _requetes_historique(etudiant)
    evenements = _evenements_justification(periodes, individuelles, request.user)

    toutes = PresenceEtudiant.objects.filter(etudiant=etudiant, present=False)
    etats = [a.etat_absence for a in toutes]
    resume = {
        'total': len(etats), 'justifiees': etats.count('justifiee'), 'soumises': etats.count('justification_soumise'),
        'en_attente': etats.count('en_attente'), 'validees': etats.count('validee'),
        'refusees': sum(1 for a in toutes if a.justif_etat == 'refusee'),
    }
    return render(request, 'etudiants/historique_justifications.html', {
        'etudiant': etudiant, 'evenements': evenements, 'resume': resume})


def historique_justifications_general(request):
    """Historique de toutes les justifications (tous les élèves de l'année affichée)."""
    if not (_peut_justifier(request.user) or _peut_decider(request.user)):
        raise PermissionDenied
    periodes, individuelles = _requetes_historique()
    evenements = _evenements_justification(periodes, individuelles, request.user)
    etat = request.GET.get('etat')
    if etat in ('soumise', 'acceptee', 'refusee'):
        evenements = [e for e in evenements if e['etat'] == etat]
    return render(request, 'etudiants/historique_justifications_general.html', {
        'evenements': evenements, 'etat': etat})


def groupes_classe_api(request):
    """Groupes actifs ayant des élèves dans la classe choisie (pour la saisie des absences et les listes de pointage)."""
    from groupes.models import Groupe
    secteur_id = request.GET.get('secteur_id')
    if not (secteur_id and secteur_id.isdigit()):
        return JsonResponse({'sections': False, 'groupes': []})
    from groupes.models import groupes_lies
    lie = groupes_lies(Secteur.objects.filter(pk=int(secteur_id)).first()).first() if Secteur.objects.filter(pk=int(secteur_id)).exists() else None
    if lie:   # la classe est représentée par un groupe : pas de choix, on indique simplement le groupe
        return JsonResponse({'lie': {'id': lie.id, 'label': lie.nom_affiche, 'effectif': lie.affectations.count()}, 'sections': False, 'groupes': []})
    groupes = list(Groupe.objects.filter(actif=True, affectations__etudiant__secteur_id=int(secteur_id)).distinct()
                   .order_by('langue', 'code'))
    return JsonResponse({
        'sections': any(g.langue == '' for g in groupes),
        'groupes': [{'id': g.id, 'label': g.nom_affiche} for g in groupes]})


# --- Listes de pointage imprimables (séances de l'emploi du temps) -------------------------------------------
JOURS_FR = ['Lundi', 'Mardi', 'Mercredi', 'Jeudi', 'Vendredi', 'Samedi', 'Dimanche']


def _eleves_des_listes(secteur, choix):
    """[(groupe ou None, [élèves])] : une liste pour toute la classe, pour un groupe, ou une liste par section."""
    from etudiant.models import ordre_matricule_croissant
    from groupes.models import Groupe, groupes_lies
    lies = list(groupes_lies(secteur))
    if lies:   # classe représentée par un ou plusieurs groupes : une liste par groupe
        return [(g, list(Etudiant.objects.filter(affectations__groupe=g).order_by(*ordre_matricule_croissant()))) for g in lies]
    tous = Etudiant.objects.filter(secteur=secteur).order_by(*ordre_matricule_croissant())
    sections = list(Groupe.objects.filter(actif=True, langue='', affectations__etudiant__secteur=secteur).distinct().order_by('code'))
    if choix.isdigit():
        g = Groupe.objects.filter(pk=int(choix), actif=True).first()
        if g:
            return [(g, list(Etudiant.objects.filter(affectations__groupe=g).order_by(*ordre_matricule_croissant())))]
    if choix == 'chaque' or (choix == '' and sections):
        listes, vus = [], set()
        for g in sections:
            membres = list(tous.filter(affectations__groupe=g))
            vus.update(e.id for e in membres)
            listes.append((g, membres))
        reste = [e for e in tous if e.id not in vus]
        if reste:
            listes.append((None, reste))
        return listes
    return [(None, list(tous))]


def _donnees_pointage(request):
    from emploie.models import EmploiDuTemps
    from groupes.models import Groupe
    from datetime import date as _date
    secteurs = Secteur.objects.all().order_by('nom')
    secteur = Secteur.objects.filter(pk=request.GET['secteur']).first() if request.GET.get('secteur', '').isdigit() else None
    try:
        jour_date = _date.fromisoformat(request.GET.get('date', ''))
    except ValueError:
        jour_date = timezone.localdate()
    ctx = {'secteurs': secteurs, 'secteur': secteur, 'date': jour_date, 'jour': JOURS_FR[jour_date.weekday()],
           'choix': request.GET.get('groupe', ''), 'groupes': [], 'seances': [], 'sections': False,
           'langue': request.GET.get('langue') if request.GET.get('langue') in ('ar', 'fr') else ('ar' if (get_language() or '').startswith('ar') else 'fr')}
    if secteur:
        from groupes.models import groupes_lies
        ctx['lie'] = list(groupes_lies(secteur))
        groupes = [] if ctx['lie'] else list(Groupe.objects.filter(actif=True, affectations__etudiant__secteur=secteur).distinct().order_by('langue', 'code'))
        ctx['groupes'] = groupes
        ctx['sections'] = any(g.langue == '' for g in groupes)
        trimestre = (Trimestre.objects.filter(debut__lte=jour_date, fin__gte=jour_date).first()
                     or Parametres.get_instance().trimestre_courant)
        ctx['seances'] = list(EmploiDuTemps.objects.filter(secteur=secteur, jour=ctx['jour'], trimestre=trimestre)
                              .select_related('matiere', 'professeur', 'salle').order_by('heure_debut'))
    return ctx


def listes_pointage(request):
    """Choix de la classe, de la date et du groupe ; affiche les séances prévues par l'emploi du temps ce jour-là."""
    ctx = _donnees_pointage(request)
    if ctx['secteur']:
        ctx['listes_apercu'] = _eleves_des_listes(ctx['secteur'], ctx['choix'])
    return render(request, 'presence_etudiant/listes_pointage.html', ctx)


def listes_pointage_imprimer(request):
    """Une page par séance (et par groupe) : N°, matricule, nom, prénom, signature."""
    ctx = _donnees_pointage(request)
    if not ctx['secteur']:
        raise Http404
    seance_id = request.GET.get('seance', 'all')
    seances = ctx['seances'] if seance_id == 'all' else [s for s in ctx['seances'] if str(s.id) == seance_id]
    listes = _eleves_des_listes(ctx['secteur'], ctx['choix'])
    ar = ctx['langue'] == 'ar'
    pages = []
    for seance in seances:
        for groupe, eleves in listes:
            lignes = [{'e': e, 'nom': (e.nom_prenom if ar else (e.nom_prenom_fr or e.nom_prenom))} for e in eleves]
            pages.append({'seance': seance, 'groupe': groupe, 'lignes': lignes})
    ctx.update({'pages': pages, 'ar': ar, 'annee': get_annee_courante()})
    return render(request, 'presence_etudiant/listes_pointage_print.html', ctx)
