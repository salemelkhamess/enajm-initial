from django import template
from django.utils import translation

from etudiant.models import Etudiant

register = template.Library()

_LIBELLES = {code: (ar, fr) for code, ar, fr in Etudiant.DIPLOMES}


@register.filter
def diplome_label(code):
    """Libellé d'un diplôme (code 'B', 'BAC'…) dans la langue active."""
    ar, fr = _LIBELLES.get(code, (code, code))
    return ar if (translation.get_language() or '').startswith('ar') else fr


@register.filter
def diplomes_ordonnes(codes):
    """Diplômes triés dans l'ordre officiel (Brevet … Doctorat)."""
    ordre = [c for c, _ar, _fr in Etudiant.DIPLOMES]
    return sorted(codes or [], key=lambda c: ordre.index(c) if c in ordre else len(ordre))


@register.filter
def fusion(nom, prenom):
    """{{ x.nom|fusion:x.prenom }} : nom + prénom sans doublon (le prénom contient souvent déjà le nom)."""
    from etudiant.noms import fusionner_noms
    return fusionner_noms(nom, prenom)
