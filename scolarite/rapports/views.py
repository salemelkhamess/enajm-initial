from collections import OrderedDict, defaultdict
from datetime import date, datetime

from django.db.models import Count, Q
from django.shortcuts import render
from django.utils import translation

from branches.models import Secteur
from emploie.models import EmploiDuTemps
from entete.models import Entete
from matiers.models import Matiere
from parametres.models import Parametres
from pointage.models import Pointage
from pointagematiere.models import PointageMatiere
from presenceetudiant.models import PresenceEtudiant, q_comptee, q_en_attente
from trimestre.models import Trimestre

HEURES_PAR_SEANCE = 2  # une absence d'élève = une séance de 2 h (comme les rapports existants)


def _is_ar():
    return (translation.get_language() or '').startswith('ar')


def _t(fr, ar):
    return ar if _is_ar() else fr


def _parse_date(value):
    try:
        return datetime.strptime(value, '%Y-%m-%d').date()
    except (TypeError, ValueError):
        return None


def _int(value):
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _filtres(request):
    """Filtres communs : période (deux dates), trimestre, secteur."""
    return {
        'date_debut': _parse_date(request.GET.get('date_debut')),
        'date_fin': _parse_date(request.GET.get('date_fin')),
        'trimestre_id': _int(request.GET.get('trimestre')),
        'secteur_id': _int(request.GET.get('secteur')),
    }


def _contexte(request, titre, filtres, **extra):
    params = Parametres.get_instance()
    ctx = {
        'titre': titre,
        'entete': Entete.objects.filter(id=1),
        'annee': params.annee_courante,
        'trimestres': Trimestre.objects.filter(annee=params.annee_courante).order_by('numero_trimestre'),
        'secteurs': Secteur.objects.all(),
        'f': filtres,
        'date_debut_str': filtres['date_debut'].strftime('%Y-%m-%d') if filtres['date_debut'] else '',
        'date_fin_str': filtres['date_fin'].strftime('%Y-%m-%d') if filtres['date_fin'] else '',
        'L': {
            'date_debut': _t('Du', 'من'),
            'date_fin': _t('Au', 'إلى'),
            'trimestre': _t('Trimestre', 'الفصل'),
            'secteur': _t('Secteur', 'القسم'),
            'tous': _t('Tous', 'الكل'),
            'filtrer': _t('Filtrer', 'تصفية'),
            'imprimer': _t('Imprimer', 'طباعة'),
            'periode': _t('Période', 'الفترة'),
            'aucune': _t('Aucune donnée pour cette période.', 'لا توجد بيانات لهذه الفترة.'),
            'total': _t('Total', 'المجموع'),
            'seances': _t('Séances', 'الحصص'),
            'heures': _t('Heures', 'الساعات'),
            'matiere': _t('Matière', 'المادة'),
            'etudiant': _t('Élève fonctionnaire', 'التلميذ الموظف'),
            'matricule': _t('Matricule', 'الرقم'),
            'professeur': _t('Professeur', 'الأستاذ'),
        },
    }
    ctx.update(extra)
    return ctx


def _plage_texte(f):
    if f['date_debut'] and f['date_fin']:
        return f"{f['date_debut']:%d/%m/%Y} - {f['date_fin']:%d/%m/%Y}"
    if f['date_debut']:
        return f"≥ {f['date_debut']:%d/%m/%Y}"
    if f['date_fin']:
        return f"≤ {f['date_fin']:%d/%m/%Y}"
    return ''


def _filtrer(qs, f, champ_date, champ_secteur=None):
    if f['date_debut']:
        qs = qs.filter(**{f'{champ_date}__gte': f['date_debut']})
    if f['date_fin']:
        qs = qs.filter(**{f'{champ_date}__lte': f['date_fin']})
    if f['trimestre_id']:
        qs = qs.filter(trimestre_id=f['trimestre_id'])
    if f['secteur_id'] and champ_secteur:
        qs = qs.filter(**{champ_secteur: f['secteur_id']})
    return qs


def _duree_heures(debut, fin):
    """Durée en heures entre deux TimeField ; 2 h par défaut si inconnue."""
    if not debut or not fin:
        return float(HEURES_PAR_SEANCE)
    delta = (datetime.combine(date.today(), fin) - datetime.combine(date.today(), debut)).total_seconds() / 3600
    return delta if delta > 0 else float(HEURES_PAR_SEANCE)


# 1. Récapitulatif des absences des élèves fonctionnaires --------------------------------------
def recap_absences_etudiants(request):
    f = _filtres(request)
    matiere_id = _int(request.GET.get('matiere'))

    qs = PresenceEtudiant.objects.filter(present=False)
    qs = _filtrer(qs, f, 'date_cours', 'etudiant__secteur_id')
    if matiere_id:
        qs = qs.filter(matiere_id=matiere_id)

    lignes = (qs.values('etudiant__secteur__nom', 'etudiant__id', 'etudiant__matricule',
                        'etudiant__nom', 'etudiant__prenom')
              .annotate(total=Count('id'),
                        justifiees=Count('id', filter=Q(is_justified=True)),
                        en_attente=Count('id', filter=q_en_attente()),
                        non_justifiees=Count('id', filter=q_comptee()))
              .order_by('etudiant__secteur__nom', 'etudiant__nom', 'etudiant__prenom'))

    groupes = OrderedDict()
    total_general = {'total': 0, 'justifiees': 0, 'non_justifiees': 0, 'en_attente': 0}
    for l in lignes:
        g = groupes.setdefault(l['etudiant__secteur__nom'], {'lignes': [], 'total': 0, 'justifiees': 0,
                                                              'non_justifiees': 0, 'en_attente': 0})
        l['total'] = l['non_justifiees']  # seules les absences validées comptent (les justifiées et celles en attente non)
        l['heures'] = l['total'] * HEURES_PAR_SEANCE
        l['heures_non_justifiees'] = l['non_justifiees'] * HEURES_PAR_SEANCE
        g['lignes'].append(l)
        for k in total_general:
            if k == 'total':
                g[k] += l['non_justifiees']
                total_general[k] += l['non_justifiees']
            else:
                g[k] += l[k]
                total_general[k] += l[k]
    for g in groupes.values():
        g['heures'] = g['total'] * HEURES_PAR_SEANCE
    total_general['heures'] = total_general['total'] * HEURES_PAR_SEANCE

    ctx = _contexte(
        request, _t("Récapitulatif des absences des élèves fonctionnaires", "ملخص غيابات التلاميذ الموظفين"), f,
        groupes=groupes.items(), total_general=total_general, plage=_plage_texte(f),
        matieres=Matiere.objects.all().order_by('nom'), matiere_id=matiere_id, avec_matiere=True,
        L2={
            'justifiees': _t('Justifiées', 'مبررة'),
            'en_attente': _t('En attente (72 h)', 'قيد الانتظار (72 ساعة)'),
            'non_justifiees': _t('Validées', 'مؤكدة'),
            'heures_nj': _t('Heures validées', 'الساعات المؤكدة'),
            'note': _t("1 séance = 2 heures", "الحصة = ساعتان"),
        })
    return render(request, 'rapports/recap_absences_etudiants.html', ctx)


# 2. Rapport des horaires d'absence des professeurs ------------------------------------------
def horaires_absences_professeurs(request):
    f = _filtres(request)

    qs = Pointage.objects.filter(etat='absent')
    qs = _filtrer(qs, f, 'date', 'seance__secteur_id')

    profs = {}
    for r in qs.values('professeur_id', 'professeur__nom', 'professeur__prenom', 'seance__matiere__nom',
                       'seance__heure_debut', 'seance__heure_fin'):
        p = profs.setdefault(r['professeur_id'], {
            'nom': f"{r['professeur__nom']} {r['professeur__prenom']}", 'seances': 0, 'heures': 0.0,
            'matieres': defaultdict(lambda: {'seances': 0, 'heures': 0.0})})
        h = _duree_heures(r['seance__heure_debut'], r['seance__heure_fin'])
        m = p['matieres'][r['seance__matiere__nom'] or '—']
        p['seances'] += 1
        p['heures'] += h
        m['seances'] += 1
        m['heures'] += h

    lignes = []
    for p in sorted(profs.values(), key=lambda x: x['nom']):
        p['matieres'] = [{'nom': n, **v} for n, v in sorted(p['matieres'].items())]
        lignes.append(p)

    total = {'seances': sum(p['seances'] for p in lignes), 'heures': sum(p['heures'] for p in lignes)}
    ctx = _contexte(request, _t("Rapport des horaires d'absence des professeurs", "تقرير ساعات غياب الأساتذة"), f,
                    professeurs=lignes, total=total, plage=_plage_texte(f))
    return render(request, 'rapports/horaires_absences_professeurs.html', ctx)


# 3. Nombre d'heures de cours par trimestre et par matière ----------------------------------
def heures_cours_par_trimestre(request):
    f = _filtres(request)

    qs = PointageMatiere.objects.all()
    qs = _filtrer(qs, f, 'date_cours', 'secteur_id')

    trims = OrderedDict()
    for r in (qs.select_related('matiere', 'trimestre')
              .order_by('trimestre__numero_trimestre', 'matiere__nom')):
        t = trims.setdefault(r.trimestre_id, {'nom': r.trimestre.nom, 'matieres': {}})
        m = t['matieres'].setdefault(r.matiere_id, {
            'nom': r.matiere.nom, 'effectuees': 0, 'annulees': 0, 'reportees': 0,
            'heures_effectuees': 0.0, 'heures_annulees': 0.0, 'heures_reportees': 0.0})
        h = r.duree()
        if r.etat == PointageMatiere.Etat.EFFECTUE:
            m['effectuees'] += 1
            m['heures_effectuees'] += h
        elif r.etat == PointageMatiere.Etat.ANNULE:
            m['annulees'] += 1
            m['heures_annulees'] += h
        else:
            m['reportees'] += 1
            m['heures_reportees'] += h

    # heures hebdomadaires prévues à l'emploi du temps, par matière
    prevues = defaultdict(float)
    for e in EmploiDuTemps.objects.filter(
            **({'trimestre_id': f['trimestre_id']} if f['trimestre_id'] else {})).values(
            'matiere_id', 'trimestre_id', 'heure_debut', 'heure_fin'):
        prevues[(e['trimestre_id'], e['matiere_id'])] += _duree_heures(e['heure_debut'], e['heure_fin'])

    resultat = []
    for tid, t in trims.items():
        lignes = sorted(t['matieres'].items(), key=lambda kv: kv[1]['nom'])
        rows = []
        tot = defaultdict(float)
        for mid, m in lignes:
            m['prevues_semaine'] = prevues.get((tid, mid), 0.0)
            rows.append(m)
            for k, v in m.items():
                if k != 'nom':
                    tot[k] += v
        resultat.append({'nom': t['nom'], 'matieres': rows, 'total': dict(tot)})

    ctx = _contexte(request, _t("Nombre d'heures de cours par trimestre et par matière",
                                "عدد ساعات الدروس حسب الفصل والمادة"), f,
                    trimestres_data=resultat, plage=_plage_texte(f),
                    L2={
                        'effectuees': _t('Séances effectuées', 'الحصص المنجزة'),
                        'h_effectuees': _t('Heures effectuées', 'الساعات المنجزة'),
                        'annulees': _t('Annulées', 'الملغاة'),
                        'reportees': _t('Reportées', 'المؤجلة'),
                        'prevues': _t('Heures prévues / semaine', 'الساعات المبرمجة أسبوعيا'),
                    })
    return render(request, 'rapports/heures_cours_trimestre.html', ctx)


# 4. Récapitulatif des absences par seuils de séances (4, 8, 12 ...) pour chaque matière ----------
def recap_absences_seuils(request):
    f = _filtres(request)
    brut = request.GET.get('seuils', '4,8,12')
    seuils = sorted({s for s in (_int(x.strip()) for x in brut.split(',')) if s and s > 0}) or [4, 8, 12]
    statut = request.GET.get('statut', 'non_justifiees')

    qs = PresenceEtudiant.objects.filter(present=False)
    if statut == 'non_justifiees':       # absences validées (72 h écoulées, non justifiées)
        qs = qs.filter(q_comptee())
    elif statut == 'justifiees':
        qs = qs.filter(is_justified=True)
    elif statut == 'en_attente':
        qs = qs.filter(q_en_attente())
    else:                                # toutes : validées + justifiées (les absences en attente ne comptent pas encore)
        qs = qs.exclude(q_en_attente())
    qs = _filtrer(qs, f, 'date_cours', 'etudiant__secteur_id')

    par_matiere = OrderedDict()
    for r in (qs.values('matiere_id', 'matiere__nom', 'matiere__secteur__nom', 'etudiant_id',
                        'etudiant__nom', 'etudiant__prenom')
              .annotate(n=Count('id')).order_by('matiere__nom', 'etudiant__nom')):
        m = par_matiere.setdefault(r['matiere_id'], {
            'nom': r['matiere__nom'], 'secteur': r['matiere__secteur__nom'], 'etudiants': []})
        m['etudiants'].append({'nom': f"{r['etudiant__nom']} {r['etudiant__prenom']}", 'n': r['n']})

    lignes = []
    totaux = {s: 0 for s in seuils}
    for m in par_matiere.values():
        colonnes = []
        for s in seuils:
            concernes = [e for e in m['etudiants'] if e['n'] >= s]
            colonnes.append({'seuil': s, 'nombre': len(concernes), 'etudiants': concernes})
            totaux[s] += len(concernes)
        m['colonnes'] = colonnes
        lignes.append(m)

    ctx = _contexte(request, _t("Récapitulatif des absences des élèves fonctionnaires par nombre de séances",
                                "ملخص غيابات التلاميذ الموظفين حسب عدد الحصص"), f,
                    lignes=lignes, seuils=seuils, seuils_str=','.join(map(str, seuils)),
                    totaux=[{'seuil': s, 'nombre': totaux[s]} for s in seuils], statut=statut,
                    plage=_plage_texte(f),
                    L2={
                        'seuils': _t('Seuils (séances)', 'العتبات (حصص)'),
                        'statut': _t('Absences', 'الغيابات'),
                        'non_justifiees': _t('Validées', 'مؤكدة'),
                        'en_attente': _t('En attente (72 h)', 'قيد الانتظار (72 ساعة)'),
                        'justifiees': _t('Justifiées', 'مبررة'),
                        'toutes': _t('Toutes', 'الكل'),
                        'au_moins': _t('au moins', 'على الأقل'),
                        'etudiants': _t('élèves', 'تلاميذ'),
                        'note': _t("1 séance = 2 heures", "الحصة = ساعتان"),
                    })
    return render(request, 'rapports/recap_absences_seuils.html', ctx)
