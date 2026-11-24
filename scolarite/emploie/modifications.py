"""
Modification de l'emploi du temps hebdomadaire avec choix de la portée.

Quand on change un créneau (matière, professeur, salle, jour ou heure), qu'on en ajoute ou qu'on en retire un,
l'utilisateur confirme si le changement vaut :

* « cette semaine et les suivantes » : le modèle hebdomadaire (EmploiDuTemps) est modifié ;
* « cette semaine seulement » : le modèle hebdomadaire ne change pas, seule la semaine en cours est concernée.

Dans les deux cas le changement est consigné dans le journal ModificationEmploi (créneau avant / après, date d'effet,
portée, auteur). L'application qualité le lit à sa synchronisation et l'applique aux séances datées à partir de la
date d'effet, jamais aux séances passées.

Un créneau est décrit par un dictionnaire (voir `creneau`) ; sa position est (jour, heure de début, heure de fin).
"""
import datetime as dt

from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone
from django.utils.translation import gettext as _

from .models import EmploiDuTemps, ModificationEmploi

JOURS_GRILLE = ['Lundi', 'Mardi', 'Mercredi', 'Jeudi', 'Vendredi']
PORTEES = (ModificationEmploi.SEMAINE, ModificationEmploi.SUIVANTES)

AJOUT, RETRAIT, MODIFICATION = 'ajout', 'retrait', 'modification'


def heure(valeur):
    """Heure (datetime.time) d'une valeur saisie (« 08:00 », « 08:00:00 ») ou déjà convertie."""
    if isinstance(valeur, dt.time):
        return valeur
    return dt.time.fromisoformat(str(valeur))


def creneau(jour, heure_debut, heure_fin, matiere_id, professeur_id, salle_id, emploi_id=None):
    """Créneau hebdomadaire : jour, heures, matière, professeur, salle ; `emploi_id` : la ligne de l'emploi du temps."""
    return {
        'jour': jour,
        'heure_debut': heure(heure_debut),
        'heure_fin': heure(heure_fin),
        'matiere_id': int(matiere_id),
        'professeur_id': int(professeur_id),
        'salle_id': int(salle_id),
        'emploi_id': emploi_id,
    }


def position(c):
    return c['jour'], c['heure_debut'], c['heure_fin']


def _contenu(c):
    return c['matiere_id'], c['professeur_id'], c['salle_id']


def identiques(a, b):
    """Même position et même contenu (matière, professeur, salle)."""
    return position(a) == position(b) and _contenu(a) == _contenu(b)


def creneau_de(emploi):
    return creneau(emploi.jour, emploi.heure_debut, emploi.heure_fin, emploi.matiere_id, emploi.professeur_id,
                   emploi.salle_id, emploi.pk)


def etat_actuel(annee_id, trimestre_id, secteur_id):
    """{position: créneau} de l'emploi du temps enregistré de la classe. Une seule ligne par position (la première,
    comme la grille) : les autres lignes éventuelles de la même position ne sont jamais touchées."""
    etat = {}
    lignes = (EmploiDuTemps._base_manager
              .filter(annee_id=annee_id, trimestre_id=trimestre_id, secteur_id=secteur_id)
              .order_by('id'))
    for emploi in lignes:
        etat.setdefault((emploi.jour, emploi.heure_debut, emploi.heure_fin), creneau_de(emploi))
    return etat


def grille_depuis_post(data, jours=JOURS_GRILLE):
    """{position: créneau} décrit par les champs de la grille ; une case sans matière, professeur ou salle est vide."""
    nouveaux = {}
    for debut, fin in zip(data.getlist('creneau_debut[]'), data.getlist('creneau_fin[]')):
        for jour in jours:
            matiere, professeur, salle = (data.get(f'{champ}_{jour}_{debut}_{fin}')
                                          for champ in ('matiere', 'professeur', 'salle'))
            if matiere and professeur and salle:
                c = creneau(jour, debut, fin, matiere, professeur, salle)
                nouveaux[position(c)] = c
    nouveau_debut, nouvelle_fin = data.get('new_creneau_debut'), data.get('new_creneau_fin')
    if nouveau_debut and nouvelle_fin:
        for jour in jours:
            matiere, professeur, salle = (data.get(f'new_{champ}_{jour}') for champ in ('matiere', 'professeur', 'salle'))
            if matiere and professeur and salle:
                c = creneau(jour, nouveau_debut, nouvelle_fin, matiere, professeur, salle)
                nouveaux[position(c)] = c
    return nouveaux


def comparer(anciens, nouveaux):
    """Changements entre deux états : liste de (avant, apres).

    (None, c) créneau ajouté ; (c, None) créneau retiré ; (c1, c2) créneau modifié. Un créneau retiré et un créneau
    ajouté de la même matière sont rapprochés en un seul changement : c'est un déplacement (autre jour ou autres
    heures), pas un retrait suivi d'un ajout."""
    changements = []
    retraits = [a for p, a in anciens.items() if p not in nouveaux]
    ajouts = [n for p, n in nouveaux.items() if p not in anciens]
    for p, apres in nouveaux.items():
        avant = anciens.get(p)
        if avant is not None and _contenu(avant) != _contenu(apres):
            changements.append((avant, apres))
    # déplacements : même matière et même professeur d'abord, puis même matière
    for critere in (lambda c: (c['matiere_id'], c['professeur_id']), lambda c: c['matiere_id']):
        for avant in list(retraits):
            apres = next((n for n in ajouts if critere(n) == critere(avant)), None)
            if apres is not None:
                retraits.remove(avant)
                ajouts.remove(apres)
                changements.append((avant, apres))
    changements += [(a, None) for a in retraits]
    changements += [(None, n) for n in ajouts]
    return changements


def nommer(changements):
    """Ajoute à chaque créneau les noms de la matière, du professeur et de la salle (copie figée dans le journal)."""
    from matiers.models import Matiere
    from professeur.models import Professeur
    from salle.models import Salle

    creneaux = [c for couple in changements for c in couple if c]
    noms = {
        'matiere': {m.pk: m.nom for m in Matiere._base_manager.filter(
            pk__in={c['matiere_id'] for c in creneaux})},
        'professeur': {p.pk: f"{p.nom} {p.prenom}".strip() for p in Professeur._base_manager.filter(
            pk__in={c['professeur_id'] for c in creneaux})},
        'salle': {s.pk: s.nom for s in Salle._base_manager.filter(pk__in={c['salle_id'] for c in creneaux})},
    }
    for c in creneaux:
        for cle in ('matiere', 'professeur', 'salle'):
            c[f'{cle}_nom'] = noms[cle].get(c[f'{cle}_id'], '')
    return changements


def _texte(c):
    horaire = f"{c['heure_debut']:%H:%M}-{c['heure_fin']:%H:%M}"
    return f"{_(c['jour'])} {horaire} : {c.get('matiere_nom', '')} ({c.get('professeur_nom', '')}, {c.get('salle_nom', '')})"


def decrire(changements):
    """Changements lisibles, pour la confirmation : [{'type', 'texte'}]."""
    nommer(changements)
    lignes = []
    for avant, apres in changements:
        if avant is None:
            lignes.append({'type': AJOUT, 'texte': _("Ajout : %(creneau)s") % {'creneau': _texte(apres)}})
        elif apres is None:
            lignes.append({'type': RETRAIT, 'texte': _("Retrait : %(creneau)s") % {'creneau': _texte(avant)}})
        else:
            lignes.append({'type': MODIFICATION, 'texte': _("%(avant)s → %(apres)s") % {
                'avant': _texte(avant), 'apres': _texte(apres)}})
    return lignes


def lundi_de(jour):
    return jour - dt.timedelta(days=jour.weekday())


def _sauver(emploi, c):
    """Enregistre la ligne ; en cas d'erreur de validation, l'exception porte le créneau fautif (`slot`)."""
    try:
        emploi.save()
    except ValidationError as e:
        e.slot = c
        raise


def _appliquer_au_modele(changements, annee_id, trimestre_id, secteur_id):
    """Modifie l'emploi du temps hebdomadaire. Un créneau qui garde sa position est mis à jour sur place (son
    identifiant ne change pas) ; un créneau qui change de jour ou d'heures est supprimé puis recréé."""
    base = EmploiDuTemps._base_manager
    for avant, apres in changements:  # d'abord les retraits : libère les positions et les contraintes d'unicité
        if avant is not None and (apres is None or position(avant) != position(apres)):
            base.filter(pk=avant['emploi_id']).delete()
    for avant, apres in changements:
        if avant is not None and apres is not None and position(avant) == position(apres):
            emploi = base.get(pk=avant['emploi_id'])
            emploi.matiere_id, emploi.professeur_id, emploi.salle_id = _contenu(apres)
            _sauver(emploi, apres)
    for avant, apres in changements:
        if apres is not None and (avant is None or position(avant) != position(apres)):
            _sauver(EmploiDuTemps(annee_id=annee_id, trimestre_id=trimestre_id, secteur_id=secteur_id,
                                  jour=apres['jour'], heure_debut=apres['heure_debut'], heure_fin=apres['heure_fin'],
                                  matiere_id=apres['matiere_id'], professeur_id=apres['professeur_id'],
                                  salle_id=apres['salle_id']), apres)


def _champs_journal(prefixe, c):
    if c is None:
        return {}
    return {
        f'{prefixe}_jour': c['jour'],
        f'{prefixe}_heure_debut': c['heure_debut'],
        f'{prefixe}_heure_fin': c['heure_fin'],
        f'{prefixe}_matiere_id': c['matiere_id'],
        f'{prefixe}_matiere_nom': c.get('matiere_nom', '')[:200],
        f'{prefixe}_professeur_id': c['professeur_id'],
        f'{prefixe}_professeur_nom': c.get('professeur_nom', '')[:250],
        f'{prefixe}_salle_id': c['salle_id'],
        f'{prefixe}_salle_nom': c.get('salle_nom', '')[:200],
    }


def consigner(changements, *, annee_id, trimestre_id, secteur_id, portee, par='', aujourdhui=None):
    """Enregistre les changements dans le journal, sans toucher à l'emploi du temps hebdomadaire.

    `date_effet` : le jour de la modification ; `date_fin` : le dimanche de cette semaine pour « cette semaine
    seulement », sinon vide (toutes les semaines suivantes). Retourne le nombre de lignes ajoutées."""
    if portee not in PORTEES:
        raise ValueError(f"Portée inconnue : {portee!r}")
    aujourdhui = aujourdhui or timezone.localdate()
    date_fin = lundi_de(aujourdhui) + dt.timedelta(days=6) if portee == ModificationEmploi.SEMAINE else None
    nommer(changements)
    ModificationEmploi.objects.bulk_create([
        ModificationEmploi(
            secteur_id=secteur_id, annee_id=annee_id, trimestre_id=trimestre_id, portee=portee,
            date_effet=aujourdhui, date_fin=date_fin, cree_par=(par or '')[:150],
            **_champs_journal('avant', avant), **_champs_journal('apres', apres))
        for avant, apres in changements])
    return len(changements)


def appliquer(changements, *, annee_id, trimestre_id, secteur_id, portee, par='', aujourdhui=None):
    """Applique les changements avec la portée choisie et les consigne dans le journal (tout ou rien).

    `suivantes` : le modèle hebdomadaire change ; `semaine` : il reste tel quel, seul le journal garde le changement.
    Retourne le nombre de changements. ValidationError (avec `slot`) si une ligne est refusée : rien n'est enregistré.
    """
    if portee not in PORTEES:
        raise ValueError(f"Portée inconnue : {portee!r}")
    with transaction.atomic():
        if portee == ModificationEmploi.SUIVANTES:
            _appliquer_au_modele(changements, annee_id, trimestre_id, secteur_id)
        return consigner(changements, annee_id=annee_id, trimestre_id=trimestre_id, secteur_id=secteur_id,
                         portee=portee, par=par, aujourdhui=aujourdhui)


def creer_emploi_initial(nouveaux, *, annee_id, trimestre_id, secteur_id):
    """Première saisie de l'emploi du temps d'une classe : les créneaux sont créés, sans confirmation ni journal."""
    with transaction.atomic():
        _appliquer_au_modele([(None, c) for c in nouveaux.values()], annee_id, trimestre_id, secteur_id)


def enregistrer_grille(nouveaux, *, annee_id, trimestre_id, secteur_id, portee=None, par='', aujourdhui=None):
    """Enregistre la grille `nouveaux` ({position: créneau}) pour la classe.

    Retourne ('inchange', []), ('initial', []) ou ('applique', changements) quand c'est fait, ('confirmer',
    changements) quand la portée est à demander (rien n'est enregistré)."""
    anciens = etat_actuel(annee_id, trimestre_id, secteur_id)
    if not anciens:
        if not nouveaux:
            return 'inchange', []
        creer_emploi_initial(nouveaux, annee_id=annee_id, trimestre_id=trimestre_id, secteur_id=secteur_id)
        return 'initial', []
    changements = comparer(anciens, nouveaux)
    if not changements:
        return 'inchange', []
    if portee not in PORTEES:
        return 'confirmer', changements
    appliquer(changements, annee_id=annee_id, trimestre_id=trimestre_id, secteur_id=secteur_id, portee=portee,
              par=par, aujourdhui=aujourdhui)
    return 'applique', changements
