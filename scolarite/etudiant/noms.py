"""Assemblage nom + prénom sans doublon (usage mauritanien : le « prénom » contient souvent déjà le nom complet)."""
import re
import unicodedata

_DIACRITIQUES = re.compile(r'[ؐ-ًؚ-ٰٟۖ-ۭـ]')


def _mots(texte):
    """Mots comparables : sans voyelles arabes, alef/ya/ta marbuta unifiés, sans accents, en minuscules."""
    t = unicodedata.normalize('NFKC', texte or '')
    t = _DIACRITIQUES.sub('', t)
    t = (t.replace('أ', 'ا').replace('إ', 'ا').replace('آ', 'ا').replace('ى', 'ي').replace('ة', 'ه')
         .replace('ؤ', 'و').replace('ئ', 'ي'))
    t = ''.join(c for c in unicodedata.normalize('NFD', t) if unicodedata.category(c) != 'Mn')
    return re.sub(r'[\s\-\'’]+', ' ', t).strip().lower().split()


def _contient(grand, petit):
    n = len(petit)
    return n > 0 and any(grand[i:i + n] == petit for i in range(len(grand) - n + 1))


def fusionner_noms(a, b):
    """« a b », mais si l'un des deux est déjà contenu (mot à mot) dans l'autre, on ne garde que le plus complet.
    Ex. : ('الشيخ أحمد', 'الشيخ أحمد السالك فال') -> 'الشيخ أحمد السالك فال'."""
    a, b = (a or '').strip(), (b or '').strip()
    if not a:
        return b
    if not b:
        return a
    ma, mb = _mots(a), _mots(b)
    if _contient(mb, ma):
        return b
    if _contient(ma, mb):
        return a
    return f"{a} {b}"
