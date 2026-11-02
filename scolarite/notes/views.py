# views.py
from django.utils import timezone

from django.shortcuts import render, get_object_or_404, redirect

from annee.models import Annee
from branches.models import Secteur
from entete.models import Entete
from etudiant.models import Etudiant
from evaluation.models import Evaluation
from matiers.models import Matiere
from trimestre.models import Trimestre
from .models import Note, NoteSpeciale
from .forms import NoteForm, BulletinForm
from django.db.models import Q, Prefetch
from django.contrib import messages
import logging
logger = logging.getLogger(__name__)
from django.utils.translation import gettext_lazy as _


def note_list(request):
    notes = Note.objects.select_related('etudiant', 'evaluation').all()
    return render(request, 'notes/note_list.html', {'notes': notes})

def note_create(request):
    if request.method == 'POST':
        form = NoteForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('note_list')
    else:
        form = NoteForm()
    return render(request, 'notes/note_form.html', {'form': form})

def note_update(request, pk):
    note = get_object_or_404(Note, pk=pk)
    if request.method == 'POST':
        form = NoteForm(request.POST, instance=note)
        if form.is_valid():
            form.save()
            return redirect('note_list')
    else:
        form = NoteForm(instance=note)
    return render(request, 'notes/note_form.html', {'form': form})

def note_delete(request, pk):
    note = get_object_or_404(Note, pk=pk)
    if request.method == 'POST':
        note.delete()
        return redirect('note_list')
    return render(request, 'notes/note_confirm_delete.html', {'object': note})


from formations.models import Formation  # Assurez-vous que c'est bien importé


def note_par_evaluation(request):
    # Initialisation des variables
    formations = Formation.objects.all()
    selected_formation_id = request.GET.get('formation')
    selected_secteur_id = request.GET.get('secteur')
    selected_trimestre_id = request.GET.get('trimestre')
    selected_type = request.GET.get('type')

    secteurs = []
    trimestres = []
    evaluations = []
    etudiants = []
    matieres_disponibles = []

    # Filtrage hiérarchique
    if selected_formation_id:
        secteurs = Secteur.objects.filter(formation_id=selected_formation_id)

    if selected_secteur_id:
        trimestres = Trimestre.objects.all()
        matieres_disponibles = Evaluation.objects.filter(
            secteur_id=selected_secteur_id
        ).values_list('matiere__id', 'matiere__nom').distinct()

    if all([selected_trimestre_id, selected_secteur_id, selected_type]):
        evaluations = Evaluation.objects.filter(
            trimestre_id=selected_trimestre_id,
            secteur_id=selected_secteur_id,
            type=selected_type
        ).select_related('matiere').prefetch_related('note_set')

        if evaluations.exists():
            etudiants = Etudiant.objects.filter(
                secteur_id=selected_secteur_id
            ).select_related('secteur').prefetch_related('note_set')

    # Gestion de la soumission du formulaire
    if request.method == 'POST':
        try:
            for evaluation in evaluations:
                for etudiant in etudiants:
                    note_key = f'note_{evaluation.id}_{etudiant.id}'
                    if note_key in request.POST and request.POST[note_key]:
                        Note.objects.update_or_create(
                            evaluation=evaluation,
                            etudiant=etudiant,
                            defaults={'note_sur_20': float(request.POST[note_key])}
                        )
            messages.success(request, _("Notes enregistrées avec succès"))
            return redirect(request.get_full_path())
        except Exception as e:
            messages.error(request, f"Erreur: {str(e)}")

    return render(request, 'notes/note_par_evaluation.html', {
        'formations': formations,
        'secteurs': secteurs,
        'trimestres': trimestres,
        'evaluations': evaluations,
        'etudiants': etudiants,
        'matieres_disponibles': matieres_disponibles,
        'selected_formation': selected_formation_id,
        'selected_secteur': selected_secteur_id,
        'selected_trimestre': selected_trimestre_id,
        'selected_type': selected_type,
    })


def note_par_evaluation_edit(request):
    # Initialisation des variables
    formations = Formation.objects.all()
    selected_formation_id = request.GET.get('formation')
    selected_secteur_id = request.GET.get('secteur')
    selected_trimestre_id = request.GET.get('trimestre')
    selected_type = request.GET.get('type')

    secteurs = []
    trimestres = []
    evaluations = []
    etudiants = []

    # Filtrage hiérarchique
    if selected_formation_id:
        secteurs = Secteur.objects.filter(formation_id=selected_formation_id)

    if selected_secteur_id:
        trimestres = Trimestre.objects.all()

    if all([selected_trimestre_id, selected_secteur_id, selected_type]):
        evaluations = Evaluation.objects.filter(
            trimestre_id=selected_trimestre_id,
            secteur_id=selected_secteur_id,
            type=selected_type
        ).select_related('matiere')

        if evaluations.exists():
            etudiants = Etudiant.objects.filter(
                secteur_id=selected_secteur_id
            ).prefetch_related(
                Prefetch('note_set',
                         queryset=Note.objects.filter(evaluation__in=evaluations),
                         to_attr='notes_filtrees')
            )

    # Gestion de la soumission du formulaire
    if request.method == 'POST':
        updated_notes = []  # Pour stocker les IDs des notes mises à jour
        try:
            for evaluation in evaluations:
                for etudiant in etudiants:
                    note_key = f'note_{evaluation.id}_{etudiant.id}'
                    if note_key in request.POST and request.POST[note_key]:
                        note, created = Note.objects.update_or_create(
                            evaluation=evaluation,
                            etudiant=etudiant,
                            defaults={
                                'note_sur_20': float(request.POST[note_key]),
                                'status': True  # Mettre le status à True
                            }
                        )
                        updated_notes.append(note.id)

            # Message de succès avec le nombre de notes mises à jour
            messages.success(request, _("notes mises à jour et validées avec succès"))
            return redirect(request.get_full_path())

        except Exception as e:
            messages.error(request, f"Erreur: {str(e)}")

    context = {
        'formations': formations,
        'secteurs': secteurs,
        'trimestres': trimestres,
        'evaluations': evaluations,
        'etudiants': etudiants,
        'selected_formation': selected_formation_id,
        'selected_secteur': selected_secteur_id,
        'selected_trimestre': selected_trimestre_id,
        'selected_type': selected_type,
    }
    return render(request, 'notes/edition_notes.html', context)

def afficher_bulletin(request):
    bulletins = None
    if request.method == 'POST':
        form = BulletinForm(request.POST)
        if form.is_valid():
            annee = form.cleaned_data['annee']
            trimestre = form.cleaned_data['trimestre']
            secteur = form.cleaned_data['secteur']
            type_eval = form.cleaned_data['type_evaluation']

            # Récupérer tous les étudiants du secteur
            etudiants = Etudiant.objects.filter(secteur=secteur, annee=annee)
            if not etudiants.exists():
                messages.warning(request, "Aucun étudiant trouvé pour ce secteur et année")
                return render(request, 'notes/bulletin.html', {'form': form})

            # Récupérer toutes les évaluations
            evaluations = Evaluation.objects.filter(
                trimestre=trimestre,
                type=type_eval,
                secteur=secteur
            )

            if not evaluations.exists():
                messages.warning(request, "Aucune évaluation trouvée pour les critères sélectionnés")
                return render(request, 'notes/bulletin.html', {'form': form})

            bulletins = []
            etudiants_sans_notes = []

            for etudiant in etudiants:
                notes = Note.objects.filter(
                    etudiant=etudiant,
                    evaluation__in=evaluations,
                    status=True
                ).select_related('evaluation', 'evaluation__matiere')

                if notes.exists():
                    total = sum(n.note_sur_20 * n.evaluation.coefficient for n in notes)
                    total_coef = sum(n.evaluation.coefficient for n in notes)
                    moyenne = round(total / total_coef, 2) if total_coef != 0 else 0

                    bulletins.append({
                        'etudiant': etudiant,
                        'notes': notes,
                        'total': total,
                        'moyenne': moyenne,
                        'trimestre': trimestre,
                        'type': type_eval,
                        'date': timezone.now().date(),
                    })
                else:
                    etudiants_sans_notes.append(etudiant)

            if not bulletins:
                messages.warning(request, _("Aucune note validée trouvée pour les critères sélectionnés"))
            elif etudiants_sans_notes:
                messages.info(request,
                              f"Données trouvées, mais {len(etudiants_sans_notes)} étudiants n'ont pas de notes validées")

    else:
        form = BulletinForm()

    entete = Entete.objects.first()
    return render(request, 'notes/bulletin.html', {
        'form': form,
        'bulletins': bulletins,
        'entete': entete,
    })


def gestion_notes_speciales(request):
    # Initialisation des variables
    formations = Formation.objects.all()
    trimestres = Trimestre.objects.all()  # Ajout de cette ligne
    selected_formation_id = request.GET.get('formation')
    selected_secteur_id = request.GET.get('secteur')
    selected_trimestre_id = request.GET.get('trimestre')

    secteurs = []
    etudiants = []

    # Filtrage hiérarchique
    if selected_formation_id:
        secteurs = Secteur.objects.filter(formation_id=selected_formation_id)

    if selected_secteur_id:
        etudiants = Etudiant.objects.filter(
            secteur_id=selected_secteur_id
        ).select_related('secteur')

        # Préchargement des notes existantes si trimestre sélectionné
        if selected_trimestre_id:
            notes_existantes = NoteSpeciale.objects.filter(
                trimestre_id=selected_trimestre_id,
                etudiant__secteur_id=selected_secteur_id
            )

            # Organisation des notes par étudiant et type
            notes_par_etudiant = {}
            for note in notes_existantes:
                if note.etudiant_id not in notes_par_etudiant:
                    notes_par_etudiant[note.etudiant_id] = {}
                notes_par_etudiant[note.etudiant_id][note.type] = note.note

            # Ajout des notes aux objets étudiants
            for etu in etudiants:
                etu.notes = {
                    'directeur': notes_par_etudiant.get(etu.id, {}).get('directeur', ''),
                    'etude': notes_par_etudiant.get(etu.id, {}).get('etude', ''),
                    'formation': notes_par_etudiant.get(etu.id, {}).get('formation', ''),
                }

    # Gestion de la soumission du formulaire
    if request.method == 'POST':
        trimestre_id = request.POST.get('trimestre')
        try:
            for key, value in request.POST.items():
                if key.startswith('note_'):
                    parts = key.split('_')
                    note_type = parts[1]
                    etudiant_id = parts[2]

                    if value:  # Si une note est fournie
                        NoteSpeciale.objects.update_or_create(
                            etudiant_id=etudiant_id,
                            trimestre_id=trimestre_id,
                            type=note_type,
                            defaults={'note': float(value)}
                        )
                    else:  # Si le champ est vide, supprimer la note
                        NoteSpeciale.objects.filter(
                            etudiant_id=etudiant_id,
                            trimestre_id=trimestre_id,
                            type=note_type
                        ).delete()

            messages.success(request, "Notes spéciales enregistrées avec succès")
            return redirect(request.get_full_path())

        except Exception as e:
            messages.error(request, f"Erreur: {str(e)}")

    return render(request, 'notes/gestion_notes_speciales.html', {
        'formations': formations,
        'trimestres': trimestres,  # Ajout de cette ligne
        'secteurs': secteurs,
        'etudiants': etudiants,
        'selected_formation': selected_formation_id,
        'selected_secteur': selected_secteur_id,
        'selected_trimestre': selected_trimestre_id,
    })