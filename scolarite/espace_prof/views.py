from datetime import date, datetime
from decimal import Decimal, InvalidOperation

from django.contrib import messages
from django.db.models import Count, Q
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.translation import gettext as _

from emploie.models import EmploiDuTemps
from etudiant.models import Etudiant
from evaluation.models import Evaluation
from notes.models import Note
from parametres.models import Parametres
from pointage.models import Pointage
from pointagematiere.models import PointageMatiere
from presenceetudiant.models import PresenceEtudiant
from trimestre.models import Trimestre

from .decorators import professeur_required
from .utils import JOURS, couples_matiere_secteur, creneaux, dernier_jour, jour_de


def _creneau(request, creneau_id):
    """Créneau demandé, uniquement s'il appartient au professeur connecté."""
    return get_object_or_404(EmploiDuTemps.objects.select_related('matiere', 'secteur', 'salle', 'trimestre', 'annee'),
                             pk=creneau_id, professeur=request.professeur)


def _date_demandee(request, creneau):
    """(date, erreur) : date choisie, qui doit tomber le bon jour de la semaine et ne pas être future."""
    brut = request.POST.get('date') or request.GET.get('date')
    try:
        d = datetime.strptime(brut, '%Y-%m-%d').date() if brut else dernier_jour(creneau.jour)
    except ValueError:
        return dernier_jour(creneau.jour), _("Date invalide.")
    if d > date.today():
        return d, _("La date ne peut pas être dans le futur.")
    if jour_de(d) != creneau.jour:
        return d, _("Cette date ne correspond pas au jour de ce cours (%(jour)s).") % {'jour': creneau.jour}
    return d, None


@professeur_required
def accueil(request):
    params = Parametres.get_instance()
    liste = creneaux(request.professeur, params.trimestre_courant)
    par_jour = [(j, [c for c in liste if c.jour == j]) for j in JOURS]
    return render(request, 'espace_prof/accueil.html', {
        'professeur': request.professeur,
        'par_jour': [(j, cs) for j, cs in par_jour if cs],
        'nb_creneaux': len(liste),
    })


@professeur_required
def absences(request, creneau_id):
    c = _creneau(request, creneau_id)
    d, erreur = _date_demandee(request, c)
    etudiants = list(Etudiant.objects.filter(secteur=c.secteur).order_by('nom', 'prenom'))
    existantes = {p.etudiant_id: p for p in PresenceEtudiant.objects.filter(
        matiere=c.matiere, date_cours=d, jour=c.jour, etudiant__in=etudiants)}

    if request.method == 'POST' and not erreur:
        nb_absents = 0
        for e in etudiants:
            absent = request.POST.get(f'absent_{e.id}') == 'on'
            justification = (request.POST.get(f'justification_{e.id}') or '').strip() if absent else ''
            PresenceEtudiant.objects.update_or_create(
                etudiant=e, matiere=c.matiere, date_cours=d, jour=c.jour,
                defaults={
                    'annee': c.annee, 'trimestre': c.trimestre, 'present': not absent,
                    'justification': justification,
                    'date_justification': date.today() if absent else None,
                    'is_justified': bool(justification) if absent else False,
                })
            nb_absents += absent
        messages.success(request, _("Présences enregistrées : %(a)s absent(s) sur %(n)s élève(s).")
                         % {'a': nb_absents, 'n': len(etudiants)})
        return redirect(f"{request.path}?date={d:%Y-%m-%d}")

    lignes = []
    for e in etudiants:
        p = existantes.get(e.id)
        lignes.append({'etudiant': e, 'absent': bool(p and not p.present), 'justification': p.justification if p else '',
                       'etat': p.etat_absence if p else None, 'heures': p.heures_avant_validation if p else 0})
    return render(request, 'espace_prof/absences.html', {
        'c': c, 'date': d, 'erreur': erreur, 'lignes': lignes, 'deja': bool(existantes),
    })


@professeur_required
def seance(request, creneau_id):
    c = _creneau(request, creneau_id)
    d, erreur = _date_demandee(request, c)
    pointage = Pointage.objects.filter(professeur=request.professeur, seance=c, date=d).first()
    cours = PointageMatiere.objects.filter(professeur=request.professeur, matiere=c.matiere, secteur=c.secteur,
                                           date_cours=d, heure_debut=c.heure_debut).first()

    if request.method == 'POST' and not erreur:
        etat = request.POST.get('etat_presence')
        etat_cours = request.POST.get('etat_cours')
        contenu = (request.POST.get('contenu') or '').strip()
        remarques = (request.POST.get('remarques') or '').strip()
        if etat not in ('present', 'retard') or etat_cours not in dict(PointageMatiere.Etat.choices):
            messages.error(request, _("Veuillez renseigner votre présence et l'état du cours."))
        elif etat_cours == PointageMatiere.Etat.EFFECTUE and not contenu:
            messages.error(request, _("Veuillez indiquer le contenu enseigné."))
        else:
            Pointage.objects.update_or_create(
                professeur=request.professeur, seance=c, date=d,
                defaults={'etat': etat, 'remarques': remarques, 'annee': c.annee, 'trimestre': c.trimestre})
            PointageMatiere.objects.update_or_create(
                professeur=request.professeur, matiere=c.matiere, secteur=c.secteur, date_cours=d,
                heure_debut=c.heure_debut,
                defaults={'annee': c.annee, 'trimestre': c.trimestre, 'heure_fin': c.heure_fin,
                          'etat': etat_cours, 'contenu': contenu, 'remarques': remarques})
            messages.success(request, _("Votre présence et le contenu enseigné sont enregistrés."))
            return redirect(f"{request.path}?date={d:%Y-%m-%d}")

    historique = (PointageMatiere.objects.filter(professeur=request.professeur, matiere=c.matiere, secteur=c.secteur)
                  .order_by('-date_cours')[:8])
    return render(request, 'espace_prof/seance.html', {
        'c': c, 'date': d, 'erreur': erreur, 'pointage': pointage, 'cours': cours, 'historique': historique,
        'etats_cours': PointageMatiere.Etat.choices,
    })


def _filtre_evaluations(prof):
    q = Q(pk__in=[])
    for matiere_id, secteur_id in couples_matiere_secteur(prof):
        q |= Q(matiere_id=matiere_id, secteur_id=secteur_id)
    return q


@professeur_required
def notes(request):
    evaluations = (Evaluation.objects.filter(_filtre_evaluations(request.professeur))
                   .select_related('matiere', 'secteur', 'trimestre')
                   .annotate(nb_notes=Count('note'), nb_en_attente=Count('note', filter=Q(note__status=False)))
                   .order_by('-date'))
    return render(request, 'espace_prof/notes.html', {'evaluations': evaluations})


@professeur_required
def evaluation_nouvelle(request):
    prof = request.professeur
    couples = sorted({(c.matiere, c.secteur) for c in creneaux(prof)}, key=lambda x: (x[0].nom, x[1].nom))
    params = Parametres.get_instance()
    trimestres = Trimestre.objects.filter(annee=params.annee_courante).order_by('numero_trimestre')

    if request.method == 'POST':
        try:
            matiere_id, secteur_id = (int(x) for x in request.POST.get('couple', '').split('-'))
            trimestre = trimestres.get(pk=int(request.POST.get('trimestre')))
            type_eval = request.POST.get('type')
            d = datetime.strptime(request.POST.get('date', ''), '%Y-%m-%d').date()
            coef = float(request.POST.get('coefficient', '').replace(',', '.'))
        except (ValueError, Trimestre.DoesNotExist, TypeError):
            messages.error(request, _("Formulaire incomplet ou invalide."))
        else:
            if (matiere_id, secteur_id) not in {(m.id, s.id) for m, s in couples}:
                messages.error(request, _("Vous ne pouvez créer une évaluation que pour une matière que vous enseignez."))
            elif type_eval not in dict(Evaluation.TYPE_CHOICES) or coef <= 0:
                messages.error(request, _("Formulaire incomplet ou invalide."))
            else:
                ev = Evaluation.objects.create(matiere_id=matiere_id, secteur_id=secteur_id, trimestre=trimestre,
                                               type=type_eval, date=d, coefficient=coef)
                messages.success(request, _("Évaluation créée. Saisissez maintenant les notes."))
                return redirect('espace_prof_notes_saisie', evaluation_id=ev.id)
    return render(request, 'espace_prof/evaluation_form.html', {
        'couples': couples, 'trimestres': trimestres, 'types': Evaluation.TYPE_CHOICES,
        'trimestre_courant': params.trimestre_courant, 'aujourdhui': date.today(),
    })


@professeur_required
def notes_saisie(request, evaluation_id):
    ev = get_object_or_404(Evaluation.objects.filter(_filtre_evaluations(request.professeur))
                           .select_related('matiere', 'secteur', 'trimestre'), pk=evaluation_id)
    etudiants = list(Etudiant.objects.filter(secteur=ev.secteur).order_by('nom', 'prenom'))
    existantes = {n.etudiant_id: n for n in Note.objects.filter(evaluation=ev)}

    if request.method == 'POST':
        enregistrees, erreurs = 0, []
        for e in etudiants:
            brut = (request.POST.get(f'note_{e.id}') or '').strip().replace(',', '.')
            if brut == '':
                continue
            try:
                valeur = float(Decimal(brut))
            except InvalidOperation:
                erreurs.append(f"{e.nom} {e.prenom}")
                continue
            if not 0 <= valeur <= 20:
                erreurs.append(f"{e.nom} {e.prenom}")
                continue
            note = existantes.get(e.id)
            if note is None:
                Note.objects.create(evaluation=ev, etudiant=e, note_sur_20=valeur, status=False)
                enregistrees += 1
            elif note.note_sur_20 != valeur:
                note.note_sur_20, note.status = valeur, False  # modifiée : à revalider
                note.save()
                enregistrees += 1
        if erreurs:
            messages.error(request, _("Note invalide (0 à 20) pour : %(liste)s") % {'liste': ', '.join(erreurs)})
        if enregistrees or not erreurs:
            messages.success(request, _("%(n)s note(s) enregistrée(s). Elles seront prises en compte au bulletin après validation.")
                             % {'n': enregistrees})
        return redirect(request.path)

    lignes = [{'etudiant': e, 'note': existantes.get(e.id)} for e in etudiants]
    return render(request, 'espace_prof/notes_saisie.html', {'ev': ev, 'lignes': lignes})
