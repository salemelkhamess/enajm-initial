"""Export / import Excel des élèves fonctionnaires (colonnes = champs de la base de données)."""
import ast
import io
import unicodedata

from django.db import transaction
from django.utils.translation import gettext as _
from openpyxl import Workbook, load_workbook
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter

from annee.models import Annee
from niveaux.models import Niveau
from branches.models import Secteur
from parametres.utils import get_annee_courante

from .models import Etudiant

# (champ de la base, description FR, description AR)
COLONNES = [
    ('matricule', 'Matricule (obligatoire, unique)', 'الرقم (إلزامي، فريد)'),
    ('nni', 'NNI (unique)', 'الرقم الوطني (فريد)'),
    ('nom', 'Nom en arabe (obligatoire)', 'الاسم العائلي بالعربية (إلزامي)'),
    ('prenom', 'Prénom en arabe', 'الاسم الشخصي بالعربية'),
    ('nom_fr', 'Nom en français', 'الاسم العائلي بالفرنسية'),
    ('prenom_fr', 'Prénom en français', 'الاسم الشخصي بالفرنسية'),
    ('date_naissance', 'Année de naissance (ex. 1989)', 'سنة الولادة (مثال 1989)'),
    ('lieu_naissance', 'Lieu de naissance en arabe', 'مكان الولادة بالعربية'),
    ('lieu_naissance_fr', 'Lieu de naissance en français', 'مكان الولادة بالفرنسية'),
    ('sexe', 'Sexe : H (homme) ou F (femme)', 'الجنس: H (ذكر) أو F (أنثى)'),
    ('telephone', 'Téléphone', 'الهاتف'),
    ('email', 'Email', 'البريد الإلكتروني'),
    ('secteur', 'Classe : nom exact du secteur (obligatoire pour un nouvel élève)', 'القسم: الاسم الدقيق للقسم (إلزامي للتلميذ الجديد)'),
    ('annee', "Année : numéro (ex. 2024). Vide = année en cours", 'السنة: الرقم (مثال 2024). فارغ = السنة الحالية'),
    ('niveau', 'Niveau de langue (facultatif) : nom français ou arabe d\'un niveau actif', 'مستوى اللغة (اختياري): الاسم الفرنسي أو العربي لمستوى نشط'),
    ('situation_amoureuse', 'Situation familiale : C (célibataire), M (marié), D (divorcé)', 'الحالة المدنية: C أعزب، M متزوج، D مطلق'),
    ('nombre_enfants', "Nombre d'enfants", 'عدد الأطفال'),
    ('diplomes', 'Diplômes séparés par des virgules : B, BAC, L, DEUG, MASTER, M, D', 'الشهادات مفصولة بفواصل: B, BAC, L, DEUG, MASTER, M, D'),
]
CHAMPS = [c[0] for c in COLONNES]


def _sans_accents(texte):
    return ''.join(c for c in unicodedata.normalize('NFKD', str(texte)) if not unicodedata.combining(c)).lower().strip()


def codes_diplomes(valeur):
    """Liste de codes de diplômes à partir du champ texte stocké (« ['B', 'BAC'] »)."""
    if not valeur:
        return []
    try:
        liste = ast.literal_eval(valeur) if isinstance(valeur, str) else valeur
        return [str(x) for x in liste]
    except Exception:
        return []


def classeur_vide(avec_exemple=True):
    wb = Workbook()
    ws = wb.active
    ws.title = 'Etudiants'
    ws.append(CHAMPS)
    gras = Font(bold=True, color='FFFFFF')
    fond = PatternFill('solid', fgColor='00A157')
    for i, nom in enumerate(CHAMPS, 1):
        cell = ws.cell(row=1, column=i)
        cell.font, cell.fill = gras, fond
        cell.alignment = Alignment(horizontal='center')
        ws.column_dimensions[get_column_letter(i)].width = max(14, len(nom) + 4)
    ws.freeze_panes = 'A2'
    aide = wb.create_sheet('Aide - مساعدة')
    aide.append(['Colonne / العمود', 'Description', 'الوصف'])
    for champ, fr, ar in COLONNES:
        aide.append([champ, fr, ar])
    aide.append([])
    aide.append(['Diplômes / الشهادات', 'B = Brevet · BAC = Baccalauréat · L = Licence · DEUG · MASTER = Master · M = Maîtrise · D = Doctorat'])
    aide.append(['', "Ne modifiez pas la 1ère ligne (noms des colonnes). Un élève existant (même matricule) est mis à jour ; les cellules vides ne modifient rien."])
    aide.append(['', 'لا تعدّلوا السطر الأول (أسماء الأعمدة). التلميذ الموجود (نفس الرقم) يُحدَّث، والخلايا الفارغة لا تغيّر شيئا.'])
    aide.column_dimensions['A'].width = 24
    aide.column_dimensions['B'].width = 90
    aide.column_dimensions['C'].width = 70
    for cell in aide[1]:
        cell.font = Font(bold=True)
    return wb, ws


def exporter(etudiants):
    wb, ws = classeur_vide()
    for e in etudiants:
        ws.append([
            e.matricule, e.nni, e.nom, e.prenom or '', e.nom_fr or '', e.prenom_fr or '',
            e.date_naissance, e.lieu_naissance or '', e.lieu_naissance_fr or '', e.sexe or '',
            e.telephone or '', e.email or '', e.secteur.nom if e.secteur_id else '',
            e.annee.numero_annee if e.annee_id else '', e.niveau.nom_fr if e.niveau_id else '', e.situation_amoureuse or '',
            e.nombre_enfants, ', '.join(codes_diplomes(e.diplomes)),
        ])
    flux = io.BytesIO()
    wb.save(flux)
    return flux.getvalue()


def modele():
    wb, ws = classeur_vide()
    ws.append(['23001', '1234567890', 'محمد', 'أحمد', 'MOHAMED', 'Ahmed', 1990, 'نواكشوط', 'Nouakchott', 'H',
               '22000000', '', '(nom exact de la classe)', '', '', 'C', 0, 'BAC, L'])
    flux = io.BytesIO()
    wb.save(flux)
    return flux.getvalue()


# ----------------------------------------------------------------------------- import
_SEXE = {'h': 'H', 'm': 'H', 'homme': 'H', 'masculin': 'H', 'ذكر': 'H', 'f': 'F', 'femme': 'F', 'feminin': 'F', 'أنثى': 'F', 'انثى': 'F'}
_SITUATION = {
    'c': 'C', 'celibataire': 'C', 'أعزب': 'C', 'عزباء': 'C',
    'm': 'M', 'marie': 'M', 'mariee': 'M', 'marie(e)': 'M', 'متزوج': 'M', 'متزوجة': 'M',
    'd': 'D', 'divorce': 'D', 'divorcee': 'D', 'divorce(e)': 'D', 'مطلق': 'D', 'مطلقة': 'D',
}
_DIPLOMES = {}
for _code, _ar, _fr in Etudiant.DIPLOMES:
    for _cle in (_code, _ar, _fr):
        _DIPLOMES[_sans_accents(_cle)] = _code


def _texte(valeur):
    if valeur is None:
        return ''
    if isinstance(valeur, float) and valeur.is_integer():
        return str(int(valeur))
    return str(valeur).strip()


class ErreurLigne(Exception):
    pass


def _entier(valeur, nom, minimum, maximum):
    brut = _texte(valeur)
    if brut == '':
        return None
    try:
        n = int(float(brut))
    except ValueError:
        raise ErreurLigne(_("%(nom)s : « %(brut)s » n'est pas un nombre") % {'nom': nom, 'brut': brut})
    if not minimum <= n <= maximum:
        raise ErreurLigne(_("%(nom)s : %(n)s hors limites (%(minimum)s-%(maximum)s)") % {'nom': nom, 'n': n, 'minimum': minimum, 'maximum': maximum})
    return n


def _lire_ligne(valeurs, secteurs, annees, annee_courante, niveaux):
    """Valeurs nettoyées d'une ligne (clé = champ de la base). Lève ErreurLigne si invalide."""
    d = {}
    d['matricule'] = _texte(valeurs.get('matricule'))
    if not d['matricule']:
        raise ErreurLigne(_("matricule manquant"))
    if len(d['matricule']) > 20:
        raise ErreurLigne(_("matricule trop long (20 caractères max)"))
    for champ, limite in (('nni', 20), ('nom', 100), ('prenom', 100), ('nom_fr', 100), ('prenom_fr', 100),
                          ('lieu_naissance', 100), ('lieu_naissance_fr', 100), ('telephone', 20)):
        t = _texte(valeurs.get(champ))
        if len(t) > limite:
            raise ErreurLigne(_("%(champ)s trop long (%(limite)s caractères max)") % {'champ': champ, 'limite': limite})
        d[champ] = t
    email = _texte(valeurs.get('email'))
    if email and '@' not in email:
        raise ErreurLigne(_("email invalide : %(email)s") % {'email': email})
    d['email'] = email
    d['date_naissance'] = _entier(valeurs.get('date_naissance'), 'date_naissance', 1900, 2100)
    d['nombre_enfants'] = _entier(valeurs.get('nombre_enfants'), 'nombre_enfants', 0, 50)

    sexe = _texte(valeurs.get('sexe'))
    if sexe:
        if _sans_accents(sexe) not in _SEXE:
            raise ErreurLigne(_("sexe invalide : « %(sexe)s » (H ou F)") % {'sexe': sexe})
        d['sexe'] = _SEXE[_sans_accents(sexe)]
    situation = _texte(valeurs.get('situation_amoureuse'))
    if situation:
        if _sans_accents(situation) not in _SITUATION:
            raise ErreurLigne(_("situation familiale invalide : « %(situation)s » (C, M ou D)") % {'situation': situation})
        d['situation_amoureuse'] = _SITUATION[_sans_accents(situation)]

    secteur = _texte(valeurs.get('secteur'))
    if secteur:
        trouves = secteurs.get(_sans_accents(secteur), [])
        if secteur.isdigit() and not trouves:
            trouves = [s for s in secteurs['__tous__'] if s.id == int(secteur)]
        if not trouves:
            raise ErreurLigne(_("classe inconnue : « %(secteur)s »") % {'secteur': secteur})
        if len(trouves) > 1:
            raise ErreurLigne(_("classe ambiguë (plusieurs secteurs nommés « %(secteur)s »)") % {'secteur': secteur})
        d['secteur'] = trouves[0]

    niveau = _texte(valeurs.get('niveau'))
    if niveau:
        trouves = niveaux.get(_sans_accents(niveau), [])
        if not trouves:
            raise ErreurLigne(_("niveau de langue inconnu : « %(niveau)s »") % {'niveau': niveau})
        if not trouves[0].actif:
            raise ErreurLigne(_("niveau de langue inactif : « %(niveau)s »") % {'niveau': niveau})
        d['niveau'] = trouves[0]

    annee = _entier(valeurs.get('annee'), 'annee', 1900, 2200)
    if annee is not None:
        if annee not in annees:
            raise ErreurLigne(_("année inconnue : %(annee)s") % {'annee': annee})
        d['annee'] = annees[annee]

    codes = []
    for jeton in _texte(valeurs.get('diplomes')).replace(';', ',').replace('،', ',').replace('/', ',').replace('|', ',').split(','):
        jeton = jeton.strip()
        if not jeton:
            continue
        code = _DIPLOMES.get(_sans_accents(jeton))
        if not code:
            raise ErreurLigne(_("diplôme inconnu : « %(jeton)s »") % {'jeton': jeton})
        if code not in codes:
            codes.append(code)
    if _texte(valeurs.get('diplomes')):
        ordre = [c for c, _a, _f in Etudiant.DIPLOMES]
        d['diplomes'] = str(sorted(codes, key=ordre.index))
    return d


def importer(fichier):
    """
    Importe un classeur .xlsx. Tout ou rien : s'il y a des erreurs, rien n'est enregistré.
    Retourne {'crees': n, 'modifies': n, 'erreurs': [(ligne, message)], 'lignes': n}.
    """
    try:
        wb = load_workbook(fichier, read_only=True, data_only=True)
    except Exception:
        return {'crees': 0, 'modifies': 0, 'lignes': 0, 'erreurs': [(0, _("Fichier illisible : utilisez un fichier .xlsx"))]}
    ws = wb.worksheets[0]
    lignes = ws.iter_rows(values_only=True)
    entete = next(lignes, None)
    if not entete:
        return {'crees': 0, 'modifies': 0, 'lignes': 0, 'erreurs': [(1, _("Fichier vide"))]}
    colonnes = {}
    for i, titre in enumerate(entete):
        cle = _sans_accents(titre or '').replace(' ', '_')
        if cle in CHAMPS:
            colonnes[cle] = i
    manquantes = [c for c in ('matricule', 'nom') if c not in colonnes]
    if manquantes:
        return {'crees': 0, 'modifies': 0, 'lignes': 0,
                'erreurs': [(1, _("Colonnes obligatoires absentes de la 1ère ligne : %(colonnes)s. Utilisez le modèle.") % {'colonnes': ', '.join(manquantes)})]}

    secteurs = {'__tous__': list(Secteur.objects.all())}
    for s in secteurs['__tous__']:
        secteurs.setdefault(_sans_accents(s.nom), []).append(s)
    annees = {a.numero_annee: a for a in Annee.objects.all()}
    niveaux = {}
    for n in Niveau.objects.all():
        for nom in (n.nom_fr, n.nom_ar):
            niveaux.setdefault(_sans_accents(nom), []).append(n)
    annee_courante = get_annee_courante()

    erreurs, preparees, vus = [], [], set()
    n = 0
    for num, ligne in enumerate(lignes, start=2):
        if ligne is None or all(v in (None, '') for v in ligne):
            continue
        n += 1
        valeurs = {c: (ligne[i] if i < len(ligne) else None) for c, i in colonnes.items()}
        try:
            d = _lire_ligne(valeurs, secteurs, annees, annee_courante, niveaux)
            if d['matricule'] in vus:
                raise ErreurLigne(_("matricule %(d_matricule)s en double dans le fichier") % {'d_matricule': d['matricule']})
            vus.add(d['matricule'])
            existant = Etudiant._base_manager.filter(matricule=d['matricule']).first()
            if existant is None:
                if not d.get('nom'):
                    raise ErreurLigne(_("nom manquant"))
                if 'secteur' not in d:
                    raise ErreurLigne(_("classe obligatoire pour un nouvel élève"))
            if d.get('nni'):
                conflit = Etudiant._base_manager.filter(nni=d['nni'])
                if existant:
                    conflit = conflit.exclude(pk=existant.pk)
                if conflit.exists():
                    raise ErreurLigne(_("NNI %(d_nni)s déjà utilisé par un autre élève") % {'d_nni': d['nni']})
            preparees.append((num, existant, d))
        except ErreurLigne as e:
            erreurs.append((num, str(e)))

    if erreurs:
        return {'crees': 0, 'modifies': 0, 'lignes': n, 'erreurs': erreurs}

    crees = modifies = 0
    with transaction.atomic():
        for num, existant, d in preparees:
            if existant is None:
                e = Etudiant(annee=d.pop('annee', annee_courante))
                crees += 1
            else:
                e = existant
                modifies += 1
                if 'annee' in d:
                    e.annee = d.pop('annee')
            d.pop('annee', None)
            for champ, valeur in d.items():
                if champ == 'matricule' or valeur is None or valeur == '':
                    if champ == 'matricule':
                        e.matricule = valeur
                    continue  # cellule vide : on ne modifie pas
                setattr(e, champ, valeur)
            if existant is None:
                e.nom = e.nom or ''
            e.save()
    return {'crees': crees, 'modifies': modifies, 'lignes': n, 'erreurs': []}
