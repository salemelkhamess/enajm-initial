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
from .models import PresenceEtudiant, q_comptee, q_en_attente
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
                'nom_complet': f"{item['etudiant__nom']} {item['etudiant__prenom']}",
                'matricule': item['etudiant__matricule'],
                'absences': []
            }

        absences_par_secteur[secteur_id]['etudiants'][etudiant_id]['absences'].append({
            'matiere': item['matiere__nom'],
            'jour': _(item['jour']),
            'date_cours': item['date_cours'].strftime('%d/%m/%Y'),  # Formatage de la date
            # les absences en attente (72 h) sont listées mais ne comptent pas encore
            'seances': item['total_absences'] - item['en_attente'],
            'heures': (item['total_absences'] - item['en_attente']) * 2,
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
            messages.error(request, _("Erreur lors de l'enregistrement: ") + str(e))
            return redirect('presence_saisie')

@require_GET
def load_trimestres(request):
    annee_id = request.GET.get('annee_id')
    if not annee_id:
        return JsonResponse({'error': 'Paramètre manquant'}, status=400)

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
        return JsonResponse({'error': str(e)}, status=500)


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
            messages.error(self.request, "Une erreur est survenue")
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
            messages.error(self.request, f"Erreur: {str(e)}")
            print("Erreur dans get_context_data:", str(e))  # Debug

        return context

    def post(self, request, *args, **kwargs):
        print("Données POST reçues:", request.POST)  # Debug
        session_data = request.session.get('presence_data')

        if not session_data:
            messages.error(request, "Session expirée, veuillez recommencer")
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

            messages.success(request, "Présences enregistrées avec succès!")
            return redirect('presence:selection')

        except Exception as e:
            messages.error(request, f"Erreur lors de l'enregistrement: {str(e)}")
            print("Erreur dans POST:", str(e))  # Debug
            return self.get(request, *args, **kwargs)

def charger_matieres(request):
    secteur_id = request.GET.get('secteur_id')
    matieres = Matiere.objects.filter(secteur_id=secteur_id).order_by('nom')
    return JsonResponse([{'id': m.id, 'nom': m.nom} for m in matieres], safe=False)

def load_matieres(request):
    secteur_id = request.GET.get('secteur_id')
    matieres = Matiere.objects.filter(secteur_id=secteur_id).order_by('nom')
    return JsonResponse([{'id': m.id, 'nom': m.nom} for m in matieres], safe=False)


class EnregistrementPresenceView(FormView):
    template_name = 'presence_etudiant/enregistrement.html'
    form_class = PresenceForm  # Assurez-vous que cette classe est importée

    def form_valid(self, form):
        try:
            self.request.session['presence_data'] = {
                'secteur_id': form.cleaned_data['secteur'].id,
                'matiere_id': form.cleaned_data['matiere'].id,
                'date_cours': form.cleaned_data['date_cours'].isoformat(),
                'jour': form.cleaned_data['jour'],
            }
            self.request.session.modified = True
            print("Session après sauvegarde:", self.request.session['presence_data'])

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
            messages.error(request, "Session expirée, veuillez recommencer")
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

            messages.success(request, "Présences enregistrées avec succès!")
            return redirect('enregistrement_presence')

        except Exception as e:
            messages.error(request, f"Erreur lors de l'enregistrement: {str(e)}")
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

            # Récupérer les étudiants
            etudiants = Etudiant.objects.filter(
                secteur_id=secteur_id,
                annee=parametres.annee_courante
            )

            # Récupérer les présences existantes
            presences = PresenceEtudiant.objects.filter(
                etudiant__secteur_id=secteur_id,
                matiere_id=matiere_id,
                date_cours=date_cours,
                jour=jour,
                trimestre=parametres.trimestre_courant
            )

            # Préparer la liste des étudiants avec leur statut
            etudiants_list = []
            for etudiant in etudiants:
                presence = presences.filter(etudiant=etudiant).first()
                etudiants_list.append({
                    'etudiant': etudiant,
                    'present': presence.present if presence else True,
                    'presence_id': presence.id if presence else None,
                })

            context.update({
                'etudiants': etudiants_list,
                'matiere': Matiere.objects.get(id=matiere_id),
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
        matieres = Matiere.objects.filter(secteur_id=secteur_id).values('id', 'nom')
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
    )

    # Convert date_cours to datetime for each absence
    for absence in absences:
        absence.date_cours_datetime = timezone.make_aware(
            datetime.combine(absence.date_cours, datetime.min.time())
        )

    return render(request, 'etudiants/liste_absence.html', {'absences': absences})


def valider_absence(request, absence_id):
    absence = get_object_or_404(PresenceEtudiant, id=absence_id)

    if request.method == 'POST':
        absence.valider_maintenant()  # validation sans attendre les 72 h
        messages.success(request, _("L'absence a été validée avec succès."))
        return redirect('liste_absences_non_justifiees')

    return render(request, 'etudiants/confirmation_validation.html', {'absence': absence})

def modifier_statut_absence(request, absence_id):
    absence = get_object_or_404(PresenceEtudiant, pk=absence_id)

    if request.method == 'POST':
        form = JustificationForm(request.POST, instance=absence)
        if form.is_valid():
            absence = form.save(commit=False)

            # Mettre à jour is_justified en fonction du status choisi
            selected_status = form.cleaned_data.get('status')
            if selected_status == '1':  # Justifié
                absence.is_justified = 1
                absence.status = 1
                # S'assurer que justification et date sont présentes
                if not absence.justification or not absence.date_justification:
                    messages.error(request, _("Une justification et une date sont requises pour valider l'absence"))
                    return render(request, 'etudiants/modifier.html', {
                        'form': form,
                        'absence': absence
                    })
            else:  # Non justifié
                absence.is_justified = 0
                absence.status = 0
                # Réinitialiser justification et date si nécessaire
                absence.justification = ''
                absence.date_justification = None

            absence.save()
            messages.success(request, _("Statut de l'absence mis à jour avec succès!"))
            return redirect('liste_absences_non_justifiees')
    else:
        form = JustificationForm(instance=absence)

    return render(request, 'etudiants/modifier.html', {
        'form': form,
        'absence': absence
    })


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
            f"{s['etudiant__nom']} {s['etudiant__prenom']} ({s['total_hours']}h)"
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