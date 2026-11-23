from django.contrib import messages
from django.db import transaction
from django.db.models import Count
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.translation import gettext as _
from django.views.decorators.http import require_POST

from etudiant.models import Etudiant, ordre_matricule_croissant
from formations.models import Formation
from niveaux.views import gestionnaire_requis
from parametres.utils import get_annee_courante
from .forms import GroupeForm
from .models import Affectation, Groupe


@gestionnaire_requis
def groupe_liste(request):
    """Groupes de l'année affichée, regroupés par bloc puis par langue."""
    inactifs = request.GET.get('inactifs') == '1'
    groupes = Groupe.objects.select_related('bloc', 'professeur', 'salle').annotate(effectif=Count('affectations'))
    bloc_id, langue = request.GET.get('bloc'), request.GET.get('langue')
    if bloc_id and bloc_id.isdigit():
        groupes = groupes.filter(bloc_id=int(bloc_id))
    if langue in ('fr', 'ar'):
        groupes = groupes.filter(langue=langue)
    elif langue == 'sec':
        groupes = groupes.filter(langue='')
    if not inactifs:
        groupes = groupes.filter(actif=True)
    return render(request, 'groupes/liste.html', {
        'groupes': groupes, 'blocs': Formation.objects.all(), 'bloc_id': bloc_id, 'langue': langue, 'inactifs': inactifs,
        'nb_inactifs': Groupe.objects.filter(actif=False).count(), 'annee': get_annee_courante(),
        'sans_groupe_fr': _eleves_sans_groupe('fr'), 'sans_groupe_ar': _eleves_sans_groupe('ar'),
    })


def _eleves_sans_groupe(langue):
    return Etudiant.objects.exclude(affectations__langue=langue).count()


@gestionnaire_requis
def groupe_creer(request):
    form = GroupeForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        groupe = form.save(commit=False)
        groupe.annee = get_annee_courante()
        groupe.save()
        messages.success(request, _("Groupe créé. Ajoutez maintenant les élèves."))
        return redirect('groupe_eleves', pk=groupe.pk)
    return render(request, 'groupes/form.html', {'form': form, 'titre': _("Nouveau groupe")})


@gestionnaire_requis
def groupe_modifier(request, pk):
    groupe = get_object_or_404(Groupe, pk=pk)
    form = GroupeForm(request.POST or None, instance=groupe)
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, _("Groupe modifié."))
        return redirect('groupe_liste')
    return render(request, 'groupes/form.html', {'form': form, 'titre': _("Modifier le groupe"), 'groupe': groupe})


@gestionnaire_requis
@require_POST
def groupe_basculer(request, pk):
    groupe = get_object_or_404(Groupe, pk=pk)
    groupe.actif = not groupe.actif
    groupe.save(update_fields=['actif'])
    messages.success(request, _("Groupe activé.") if groupe.actif else _("Groupe désactivé."))
    return redirect('groupe_liste')


@gestionnaire_requis
@require_POST
def groupe_supprimer(request, pk):
    """Suppression possible seulement pour un groupe vide (sinon : le désactiver)."""
    groupe = get_object_or_404(Groupe, pk=pk)
    if groupe.affectations.exists():
        messages.error(request, _("Ce groupe contient des élèves : retirez-les d'abord, ou désactivez le groupe."))
    else:
        groupe.delete()
        messages.success(request, _("Groupe supprimé."))
    return redirect('groupe_liste')


@gestionnaire_requis
def groupe_eleves(request, pk):
    """Choix des élèves du groupe (liste à sélection multiple). Un élève déjà dans un autre groupe de la même
    langue y est déplacé automatiquement (et signalé)."""
    groupe = get_object_or_404(Groupe.objects.select_related('bloc'), pk=pk)
    eleves = list(Etudiant.objects.select_related('secteur').order_by('secteur__nom', *ordre_matricule_croissant()))
    par_id = {e.id: e for e in eleves}

    if request.method == 'POST':
        choisis = {int(i) for i in request.POST.getlist('etudiants') if i.isdigit() and int(i) in par_id}
        actuels = {a.etudiant_id: a for a in groupe.affectations.all()}
        deplaces, ajoutes, retires = [], 0, 0
        with transaction.atomic():
            for eid in choisis - set(actuels):
                ancienne = Affectation.objects.filter(etudiant_id=eid, langue=groupe.langue).select_related('groupe').first()
                if ancienne:
                    deplaces.append(f"{par_id[eid].nom_complet_langue} ({ancienne.groupe.nom_affiche} → {groupe.nom_affiche})")
                    ancienne.groupe = groupe
                    ancienne.niveau_eleve = ''
                    ancienne.save()
                else:
                    Affectation.objects.create(groupe=groupe, etudiant_id=eid)
                    ajoutes += 1
            for eid in set(actuels) - choisis:
                actuels[eid].delete()
                retires += 1
            # niveau individuel (facultatif) des élèves restés dans le groupe
            for eid in choisis & set(actuels):
                if f'niveau_{eid}' not in request.POST:
                    continue   # champ absent : on ne touche pas au niveau existant
                niveau = (request.POST.get(f'niveau_{eid}') or '').strip()[:20]
                if niveau != actuels[eid].niveau_eleve:
                    actuels[eid].niveau_eleve = niveau
                    actuels[eid].save(update_fields=['niveau_eleve'])
        messages.success(request, _("Groupe %(code)s enregistré : %(n)d élève(s) — %(a)d ajouté(s), %(r)d retiré(s), %(d)d déplacé(s).") % {
            'code': groupe.nom_affiche, 'n': len(choisis), 'a': ajoutes, 'r': retires, 'd': len(deplaces)})
        if deplaces:
            messages.warning(request, _("Déplacés depuis un autre groupe de la même langue : ") + " ; ".join(deplaces))
        return redirect('groupe_eleves', pk=groupe.pk)

    membres = {a.etudiant_id: a for a in groupe.affectations.select_related('etudiant')}
    # groupe actuel de chaque élève pour la même langue (affiché dans la liste de choix)
    autre = {a.etudiant_id: a.groupe.nom_affiche for a in Affectation.objects.filter(langue=groupe.langue).exclude(groupe=groupe).select_related('groupe')}
    options = [{'e': e, 'choisi': e.id in membres, 'autre': autre.get(e.id, '')} for e in eleves]
    lignes_membres = [{'e': par_id[i], 'niveau': a.niveau_eleve} for i, a in membres.items() if i in par_id]
    lignes_membres.sort(key=lambda x: (x['e'].secteur.nom, len(x['e'].matricule), x['e'].matricule))
    return render(request, 'groupes/eleves.html', {
        'groupe': groupe, 'options': options, 'membres': lignes_membres,
        'classes': sorted({(e.secteur_id, e.secteur.nom) for e in eleves}, key=lambda x: x[1])})


@gestionnaire_requis
def groupe_imprimer(request, pk):
    """Liste de présence du groupe (avec colonne d'émargement), comme les listes affichées sur papier."""
    groupe = get_object_or_404(Groupe.objects.select_related('bloc', 'professeur', 'salle', 'annee'), pk=pk)
    affectations = list(groupe.affectations.select_related('etudiant__secteur'))
    affectations.sort(key=lambda a: (len(a.etudiant.matricule), a.etudiant.matricule))
    lignes = [{'a': a, 'e': a.etudiant, 'nom': a.etudiant.nom_complet_fr if groupe.langue == 'fr' and a.etudiant.nom_complet_fr
               else a.etudiant.nom_complet_ar} for a in affectations]
    return render(request, 'groupes/imprimer.html', {
        'groupe': groupe, 'lignes': lignes, 'ar': groupe.langue != 'fr',
        'avec_niveau': any(a.niveau_eleve for a in affectations), 'emargement': request.GET.get('emargement', '1') != '0'})
