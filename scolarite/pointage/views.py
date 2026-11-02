from django.utils.translation import gettext as _
from django.utils.translation import get_language
from django.views.generic import ListView, CreateView, UpdateView, DeleteView, TemplateView
from entete.models import Entete
from datetime import datetime
from django.contrib import messages
from django.db import transaction
from django.shortcuts import render
from django.views.generic.edit import CreateView
from django.urls import reverse_lazy
from django.http import HttpResponseRedirect
from .forms import PointageForm
from emploie.models import EmploiDuTemps
from django.db.models import Count, F, Q
from django.http import JsonResponse
from .models import Pointage
from parametres.models import Parametres

class PointageListView(ListView):
    model = Pointage
    template_name = 'pointages/pointage_list.html'
    context_object_name = 'pointages'

    def get_queryset(self):
        queryset = super().get_queryset().select_related(
            'professeur', 'seance__matiere', 'seance__salle')
        # Filtrage par professeur si spécifié
        professeur_id = self.request.GET.get('professeur')
        if professeur_id:
            queryset = queryset.filter(professeur_id=professeur_id)
        return queryset

class PointageCreateView(CreateView):
    model = Pointage
    form_class = PointageForm
    template_name = 'pointages/pointage_form.html'
    success_url = reverse_lazy('pointage_list')

    def get_initial(self):
        initial = super().get_initial()
        # Récupérer l'année et le trimestre courants depuis les paramètres
        parametres = Parametres.get_instance()
        initial['annee'] = parametres.annee_courante
        initial['trimestre'] = parametres.trimestre_courant
        return initial

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['LANGUAGE_CODE'] = get_language()

        # Récupérer les paramètres courants
        parametres = Parametres.get_instance()
        context['annee_courante'] = parametres.annee_courante
        context['trimestre_courant'] = parametres.trimestre_courant

        if self.request.method == 'POST':
            secteur_id = self.request.POST.get('secteur')
            jour = self.request.POST.get('jour')

            if secteur_id and jour:
                seances = EmploiDuTemps.objects.filter(
                    secteur_id=secteur_id,
                    jour=jour
                ).select_related('professeur')

                seances_data = []
                for seance in seances:
                    seances_data.append({
                        'id': seance.id,
                        'matiere': seance.matiere.nom if hasattr(seance.matiere, 'nom') else str(seance.matiere),
                        'professeur': seance.professeur.nom if hasattr(seance.professeur, 'nom') else str(seance.professeur),
                        'heure_debut': seance.heure_debut.strftime('%H:%M'),
                        'heure_fin': seance.heure_fin.strftime('%H:%M'),
                        'etat': self.request.POST.get(f'etat_{seance.id}', 'present'),
                        'remarques': self.request.POST.get(f'remarques_{seance.id}', '')
                    })
                context['seances_data'] = seances_data
        return context

    def get_success_url(self):
        return reverse_lazy('pointage_list')

    def form_valid(self, form):
        parametres = Parametres.get_instance()

        secteur = form.cleaned_data['secteur']
        jour = form.cleaned_data['jour']
        date = form.cleaned_data['date']
        annee =parametres.annee_courante
        trimestre = parametres.trimestre_courant

        existing_pointages = Pointage.objects.filter(date=date)
        if existing_pointages.exists():
            form.add_error(None, f"Des pointages existent déjà pour la date {date}.")
            return self.form_invalid(form)

        seances = EmploiDuTemps.objects.filter(
            secteur=secteur,
            jour=jour
        ).select_related('professeur')

        pointages_a_creer = []
        for seance in seances:
            if not Pointage.objects.filter(
                    professeur=seance.professeur,
                    seance=seance,
                    date=date
            ).exists():
                pointages_a_creer.append(Pointage(
                    professeur=seance.professeur,
                    seance=seance,
                    date=date,
                    annee=annee,
                    trimestre=trimestre,
                    etat=self.request.POST.get(f'etat_{seance.id}', 'present'),
                    remarques=self.request.POST.get(f'remarques_{seance.id}', '')
                ))

        with transaction.atomic():
            Pointage.objects.bulk_create(pointages_a_creer)

        messages.success(self.request, f"{len(pointages_a_creer)} pointage(s) créé(s).")
        return HttpResponseRedirect(self.get_success_url())

class PointageUpdateView(UpdateView):
    model = Pointage
    form_class = PointageForm
    template_name = 'pointages/pointage_form.html'
    success_url = reverse_lazy('pointage_list')

    def get_initial(self):
        initial = super().get_initial()
        pointage = self.get_object()
        initial['secteur'] = pointage.seance.secteur
        initial['jour'] = pointage.seance.jour
        initial['date'] = pointage.date  # Laisser Django gérer le format
        initial['annee'] = pointage.annee
        initial['trimestre'] = pointage.trimestre
        return initial

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        pointage = self.get_object()
        # Assure que l'instance a bien la date
        kwargs['instance'].date = pointage.date
        return kwargs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        pointage = self.get_object()

        # Récupérer les paramètres courants pour affichage
        parametres = Parametres.get_instance()
        context['annee_courante'] = parametres.annee_courante
        context['trimestre_courant'] = parametres.trimestre_courant

        seances = EmploiDuTemps.objects.filter(
            secteur=pointage.seance.secteur,
            jour=pointage.seance.jour
        ).select_related('professeur', 'matiere')

        seances_data = []
        for seance in seances:
            existing_pointage = Pointage.objects.filter(
                professeur=seance.professeur,
                seance=seance,
                date=pointage.date
            ).first()

            seances_data.append({
                'id': seance.id,
                'matiere': seance.matiere.nom,
                'professeur': seance.professeur.nom,
                'heure_debut': seance.heure_debut.strftime('%H:%M'),
                'heure_fin': seance.heure_fin.strftime('%H:%M'),
                'etat': existing_pointage.etat if existing_pointage else 'present',
                'remarques': existing_pointage.remarques if existing_pointage else ''
            })

        context['seances_data'] = seances_data
        context['is_update'] = True
        return context

    def form_valid(self, form):
        try:
            pointage = self.get_object()  # Récupère le pointage existant
            parametres = Parametres.get_instance()

            # Mettre à jour les champs du pointage
            pointage.seance = EmploiDuTemps.objects.get(
                secteur=form.cleaned_data['secteur'],
                jour=form.cleaned_data['jour'],
                professeur=pointage.professeur
            )
            pointage.date = form.cleaned_data['date']
            pointage.annee = parametres.annee_courante
            pointage.trimestre = parametres.trimestre_courant

            # Mettre à jour l'état et les remarques
            pointage.etat = self.request.POST.get(f'etat_{pointage.seance.id}', 'present')
            pointage.remarques = self.request.POST.get(f'remarques_{pointage.seance.id}', '')

            pointage.save()

            messages.success(self.request, _("Pointage mis à jour avec succès."))
            return HttpResponseRedirect(self.get_success_url())

        except Exception as e:
            print(f"Error in form_valid: {str(e)}")
            form.add_error(None, f"Une erreur est survenue: {str(e)}")
            return self.form_invalid(form)

class PointageDeleteView(DeleteView):
    model = Pointage
    success_url = reverse_lazy('pointage_list')



def load_seances(request):
    secteur_id = request.GET.get('secteur')
    jour = request.GET.get('jour')

    seances = EmploiDuTemps.objects.filter(
        secteur_id=secteur_id,
        jour=jour
    ).order_by('heure_debut').select_related('professeur', 'matiere')

    data = [{
        'id': s.id,
        'matiere': s.matiere.nom,
        'professeur': s.professeur.nom,
        'heure_debut': s.heure_debut.strftime('%H:%M'),
        'heure_fin': s.heure_fin.strftime('%H:%M'),
    } for s in seances]

    return JsonResponse(data, safe=False)

def rapport_absences_detaille(request):
    date_debut = request.GET.get('date_debut')
    date_fin = request.GET.get('date_fin')

    filtres = {'etat': 'absent', 'seance__isnull': False}

    if date_debut and date_fin:
        try:
            date_debut_parsed = datetime.strptime(date_debut, '%Y-%m-%d').date()
            date_fin_parsed = datetime.strptime(date_fin, '%Y-%m-%d').date()
            filtres['date__range'] = [date_debut_parsed, date_fin_parsed]
        except ValueError:
            pass  # en cas de date invalide, on ignore le filtre

    absences = Pointage.objects.filter(**filtres)\
        .values(
            'professeur__nom',
            'seance__matiere__nom',
            'seance__secteur__nom'
        )\
        .annotate(nombre_absences=Count('id'))\
        .order_by('-nombre_absences')

    entete = Entete.objects.first()
    return render(request, 'rapports/absences_par_matiere.html', {
        'absences': absences,
        'entete': entete,
        'date_debut': date_debut,
        'date_fin': date_fin,
    })


class AbsencesProfesseursView(TemplateView):
    template_name = 'pointages/absences_professeurs.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # Récupérer les paramètres courants
        params = Parametres.get_instance()

        # Récupérer le nombre d'heures
        heures_demandees = self.request.GET.get('heures', 12)
        try:
            heures_demandees = int(heures_demandees)
        except ValueError:
            heures_demandees = 12

        # Requête pour les absences
        absences = Pointage.objects.filter(
            etat='absent',
            annee=params.annee_courante,
            trimestre=params.trimestre_courant
        ).values(
            'professeur__id',
            'professeur__nom',
            'professeur__prenom'
        ).annotate(
            nombre_absences=Count('id'),
            nombre_heures=F('nombre_absences') * 2
        ).filter(
            nombre_heures__gte=heures_demandees
        ).order_by('professeur__nom')

        entete = Entete.objects.filter(id=1)

        context.update({
            'annee': params.annee_courante,
            'trimestre': params.trimestre_courant,
            'seuil_heures': heures_demandees,
            'seuil_seances': heures_demandees // 2,
            'professeurs': absences,
            'entete': entete,
        })

        return context