from django.contrib import messages
from django.db import transaction
from django.db.models import Count
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import translation
from django.utils.translation import gettext as _
from django.views.decorators.http import require_POST

from etudiant.models import Etudiant, ordre_matricule_croissant
from etudiant.noms import _mots
from formations.models import Formation
from niveaux.views import gestionnaire_requis
from parametres.utils import get_annee_courante
from .forms import GroupeForm
from .models import Affectation, Groupe, TransfertGroupe, retirer_eleve, transferer_eleve


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
    """Membres d'un groupe : niveau individuel de chacun et transfert vers un autre groupe du même type
    (voir `groupe_transferer`). Pour ajouter ou retirer un élève : sa fiche « Groupes / transférer »."""
    groupe = get_object_or_404(Groupe.objects.select_related('bloc'), pk=pk)
    section = groupe.langue == ''   # une section = une classe : composition en lecture seule ici

    if request.method == 'POST':
        if section:
            messages.error(request, _("Les sections correspondent aux classes : leur composition ne se modifie pas ici."))
        elif request.POST.get('action') == 'niveaux':
            n = 0
            for a in groupe.affectations.all():
                cle = f'niveau_{a.etudiant_id}'
                if cle in request.POST:
                    niveau = request.POST[cle].strip()[:20]
                    if niveau != a.niveau_eleve:
                        a.niveau_eleve = niveau
                        a.save(update_fields=['niveau_eleve'])
                        n += 1
            messages.success(request, _("Niveaux individuels enregistrés (%(n)d modifié(s)).") % {'n': n})
        return redirect('groupe_eleves', pk=groupe.pk)

    arabe = (translation.get_language() or '').startswith('ar')
    cle_tri = lambda e: ((e.secteur.nom if arabe else e.secteur.nom_francais), ' '.join(_mots(e.nom_complet_langue)))
    membres = sorted(({'e': a.etudiant, 'niveau': a.niveau_eleve} for a in groupe.affectations.select_related('etudiant__secteur')),
                     key=lambda x: cle_tri(x['e']))
    destinations = [] if section else list(Groupe.objects.filter(actif=True, langue=groupe.langue).exclude(pk=groupe.pk)
                                           .select_related('bloc').order_by('bloc__nom', 'code'))
    return render(request, 'groupes/eleves.html', {'groupe': groupe, 'section': section, 'membres': membres, 'destinations': destinations})


@gestionnaire_requis
def groupe_imprimer(request, pk):
    """Liste de présence du groupe (avec colonne d'émargement), comme les listes affichées sur papier."""
    groupe = get_object_or_404(Groupe.objects.select_related('bloc', 'professeur', 'salle', 'annee'), pk=pk)
    affectations = list(groupe.affectations.select_related('etudiant__secteur'))
    affectations.sort(key=lambda a: (len(a.etudiant.matricule), a.etudiant.matricule))
    # langue de la liste : choisie (?langue=fr|ar), sinon celle du groupe ; un groupe « section » suit la langue de l'écran
    from django.utils.translation import get_language
    langue = request.GET.get('langue')
    if langue not in ('fr', 'ar'):
        langue = groupe.langue or ('ar' if (get_language() or '').startswith('ar') else 'fr')
    lignes = [{'a': a, 'e': a.etudiant, 'nom': a.etudiant.nom_complet_fr if langue == 'fr' and a.etudiant.nom_complet_fr
               else a.etudiant.nom_complet_ar} for a in affectations]
    # filière (classe / section) de chaque élève, dans la langue de la liste
    for l in lignes:
        l['filiere'] = l['e'].secteur.nom if langue == 'ar' else l['e'].secteur.nom_francais
    # tri : par filière puis ordre alphabétique (défaut), alphabétique seul, ou par matricule
    from etudiant.noms import _mots
    tri = request.GET.get('tri') if request.GET.get('tri') in ('nom', 'matricule') else 'filiere'
    cle_nom = lambda l: (' '.join(_mots(l['nom'])), len(l['e'].matricule), l['e'].matricule)
    if tri == 'filiere':
        lignes.sort(key=lambda l: (' '.join(_mots(l['filiere'])),) + cle_nom(l))
    elif tri == 'nom':
        lignes.sort(key=cle_nom)
    else:
        lignes.sort(key=lambda l: (len(l['e'].matricule), l['e'].matricule))
    for i, l in enumerate(lignes):   # séparateur visuel quand la filière change
        l['nouvelle_filiere'] = tri == 'filiere' and i > 0 and l['filiere'] != lignes[i - 1]['filiere']
    return render(request, 'groupes/imprimer.html', {
        'groupe': groupe, 'lignes': lignes, 'tri': tri, 'ar': langue == 'ar', 'langue': langue,
        'avec_niveau': any(a.niveau_eleve for a in affectations), 'emargement': request.GET.get('emargement', '1') != '0'})


@gestionnaire_requis
@require_POST
def groupe_transferer(request, pk):
    """Transfère les élèves cochés du groupe `pk` vers un autre groupe du même type."""
    source = get_object_or_404(Groupe, pk=pk)
    ids = {int(i) for i in (request.POST.getlist('transfert') + request.POST.getlist('retrait')) if i.isdigit()}
    dest = Groupe.objects.filter(pk=request.POST.get('destination') or 0, actif=True).first()
    if source.langue == '':
        messages.error(request, _("Les sections correspondent aux classes : on ne transfère pas d'élève d'une classe à une autre ici."))
    elif not dest:
        messages.error(request, _("Choisissez le groupe de destination."))
    elif dest.langue != source.langue:
        messages.error(request, _("Le transfert se fait vers un groupe du même type (français, arabe ou section)."))
    elif dest.pk == source.pk:
        messages.error(request, _("Le groupe de destination est le groupe actuel."))
    elif not ids:
        messages.error(request, _("Cochez au moins un élève à transférer."))
    else:
        niveau = (request.POST.get('niveau') or '').strip()[:20]
        faits = []
        with transaction.atomic():
            for e in Etudiant.objects.filter(pk__in=ids, affectations__groupe=source):
                transferer_eleve(e, dest, par=request.user, niveau=niveau)
                faits.append(e.nom_complet_langue)
        messages.success(request, _("%(n)d élève(s) transféré(s) de %(a)s vers %(b)s : %(noms)s") % {
            'n': len(faits), 'a': source.nom_affiche, 'b': dest.nom_affiche, 'noms': " ; ".join(faits)})
    return redirect('groupe_eleves', pk=source.pk)


from django.utils.translation import gettext_lazy as _l
TYPES = [('fr', _l("Français")), ('ar', _l("Arabe")), ('', _l("Section"))]


@gestionnaire_requis
def eleve_groupes(request, etudiant_id):
    """Groupes d'un élève (un par type) : changer de groupe / de niveau, ou quitter un groupe."""
    etudiant = get_object_or_404(Etudiant.objects.select_related('secteur'), pk=etudiant_id)
    actuels = {a.langue: a for a in Affectation.objects.filter(etudiant=etudiant).select_related('groupe')}
    groupes = list(Groupe.objects.filter(actif=True).select_related('bloc').order_by('langue', 'bloc__nom', 'code'))
    if request.method == 'POST':
        changements = []
        with transaction.atomic():
            for langue, _libelle in TYPES:
                if langue == '':
                    continue   # section = classe : jamais modifiée depuis cette page
                cle = 'groupe_' + (langue or 'sec')
                choix = request.POST.get(cle, '')
                niveau = (request.POST.get('niveau_' + (langue or 'sec')) or '').strip()[:20]
                actuel = actuels.get(langue)
                if choix == 'aucun' and actuel:
                    retirer_eleve(etudiant, langue, par=request.user)
                    changements.append(_("%(g)s : retiré") % {'g': actuel.groupe.nom_affiche})
                elif choix.isdigit():
                    dest = next((g for g in groupes if g.pk == int(choix) and g.langue == langue), None)
                    if dest and (not actuel or actuel.groupe_id != dest.pk):
                        transferer_eleve(etudiant, dest, par=request.user, niveau=niveau)
                        changements.append(_("%(a)s → %(b)s") % {'a': actuel.groupe.nom_affiche if actuel else '—', 'b': dest.nom_affiche})
                    elif dest and actuel and niveau != actuel.niveau_eleve:
                        actuel.niveau_eleve = niveau
                        actuel.save(update_fields=['niveau_eleve'])
                        changements.append(_("niveau de %(g)s : %(n)s") % {'g': dest.nom_affiche, 'n': niveau or '—'})
        messages.success(request, _("Groupes de %(nom)s mis à jour : %(c)s") % {
            'nom': etudiant.nom_complet_langue, 'c': " ; ".join(str(c) for c in changements)} if changements
            else _("Aucun changement pour %(nom)s.") % {'nom': etudiant.nom_complet_langue})
        return redirect('eleve_groupes', etudiant_id=etudiant.pk)
    lignes = [{'langue': l, 'libelle': lib, 'cle': l or 'sec', 'actuel': actuels.get(l), 'lecture_seule': l == '',
               'options': [] if l == '' else [g for g in groupes if g.langue == l]} for l, lib in TYPES]
    historique = TransfertGroupe.objects.filter(etudiant=etudiant).select_related('de_groupe', 'vers_groupe', 'par')[:15]
    return render(request, 'groupes/eleve_groupes.html', {'etudiant': etudiant, 'lignes': lignes, 'historique': historique})
