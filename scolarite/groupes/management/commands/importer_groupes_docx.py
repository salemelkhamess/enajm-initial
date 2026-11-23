"""
Importe les groupes et leurs élèves depuis les listes Word de la scolarité (dossier docs) :

  * « ENAJM Bloc … Affichage.docx »  : groupes de FRANÇAIS (G1Ad, G2, G1F…), élèves repérés par leur MATRICULE ;
  * « Groupe A/B … العربية … .docx »  : groupes d'ARABE (GAar, GBar), élèves repérés par leur NOM (arabe), avec niveau individuel.

Usage :  python manage.py importer_groupes_docx /chemin/vers/docs [--dry-run] [--annee-id N]
Rien n'est écrit avec --dry-run. Les noms ambigus ou introuvables ne sont jamais rattachés au hasard : ils sont listés.
"""
import difflib
import re
import unicodedata
import xml.etree.ElementTree as ET
import zipfile
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from annee.models import Annee
from etudiant.models import Etudiant
from formations.models import Formation
from groupes.models import Affectation, Groupe
from parametres.models import Parametres
from salle.models import Salle

W = '{http://schemas.openxmlformats.org/wordprocessingml/2006/main}'


def _txt(el):
    return ''.join(t.text or '' for t in el.iter(W + 't')).strip()


def lire_docx(chemin):
    """Suite ordonnée d'éléments : ('p', texte) ou ('tbl', [[cellules…], …])."""
    with zipfile.ZipFile(chemin) as z:
        racine = ET.fromstring(z.read('word/document.xml'))
    blocs = []
    for el in racine.find(W + 'body'):
        if el.tag == W + 'p':
            t = _txt(el)
            if t:
                blocs.append(('p', t))
        elif el.tag == W + 'tbl':
            blocs.append(('tbl', [[_txt(tc) for tc in tr.findall(W + 'tc')] for tr in el.iter(W + 'tr')]))
    return blocs


_DIACRITIQUES = re.compile(r'[ؐ-ًؚ-ٰٟۖ-ۭـ]')


def normaliser(texte):
    """Forme comparable d'un nom arabe : sans voyelles/tatweel, alef/ya/ta marbuta unifiés, espaces réduits."""
    t = unicodedata.normalize('NFKC', texte or '')
    t = _DIACRITIQUES.sub('', t)
    t = (t.replace('أ', 'ا').replace('إ', 'ا').replace('آ', 'ا').replace('ى', 'ي').replace('ة', 'ه')
         .replace('ؤ', 'و').replace('ئ', 'ي'))
    return re.sub(r'\s+', ' ', t).strip().lower()


def score(a, b):
    """Ressemblance de deux noms normalisés : meilleur de la similarité de séquence et du recouvrement de mots."""
    if not a or not b:
        return 0.0
    ta, tb = set(a.split()), set(b.split())
    jaccard = len(ta & tb) / len(ta | tb)
    return max(difflib.SequenceMatcher(None, a, b).ratio(), jaccard)


class Command(BaseCommand):
    help = "Importe les groupes (français / arabe) et leurs élèves depuis les fichiers Word du dossier docs."

    def add_arguments(self, parser):
        parser.add_argument('dossier', help="Dossier contenant les fichiers .docx")
        parser.add_argument('--dry-run', action='store_true', help="Simule : n'écrit rien dans la base")
        parser.add_argument('--annee-id', type=int, help="Année (par défaut : année active des paramètres)")

    # ------------------------------------------------------------------------------------------------
    def handle(self, *args, **opts):
        dossier = Path(opts['dossier'])
        if not dossier.is_dir():
            raise CommandError(f"Dossier introuvable : {dossier}")
        self.dry = opts['dry_run']
        self.annee = Annee.objects.get(pk=opts['annee_id']) if opts['annee_id'] else Parametres.get_real_instance().annee_courante
        self.eleves = list(Etudiant._base_manager.filter(annee=self.annee).select_related('secteur'))
        self.par_matricule = {e.matricule: e for e in self.eleves}
        self.rapport = {'groupes': 0, 'membres': 0, 'introuvables': [], 'ambigus': [], 'professeurs': []}
        self.stdout.write(f"Année {self.annee} — {len(self.eleves)} élèves — {'SIMULATION' if self.dry else 'ÉCRITURE'}")

        with transaction.atomic():
            for fichier in sorted(dossier.glob('*.docx')):
                blocs = lire_docx(fichier)
                if 'Bloc' in fichier.name:
                    self.importer_francais(fichier.name, blocs)
                elif fichier.name.startswith('Groupe'):
                    self.importer_arabe(fichier.name, blocs)
                else:
                    self.stdout.write(self.style.WARNING(f"Ignoré : {fichier.name}"))
            if self.dry:
                transaction.set_rollback(True)

        r = self.rapport
        self.stdout.write(self.style.SUCCESS(f"\n{r['groupes']} groupe(s), {r['membres']} affectation(s)."))
        for titre, cle in (("Matricules / noms INTROUVABLES", 'introuvables'), ("Noms AMBIGUS (non rattachés)", 'ambigus')):
            if r[cle]:
                self.stdout.write(self.style.WARNING(f"\n{titre} ({len(r[cle])}) :"))
                for ligne in r[cle]:
                    self.stdout.write(f"  - {ligne}")
        if r['professeurs']:
            self.stdout.write(self.style.WARNING("\nProfesseurs saisis en texte libre (à relier si besoin) :"))
            for ligne in r['professeurs']:
                self.stdout.write(f"  - {ligne}")

    # ------------------------------------------------------------------------------------------------
    def formation(self, mot_cle):
        for f in Formation.objects.all():
            if mot_cle in f.nom:
                return f
        return None

    def salle(self, numero):
        return Salle.objects.filter(nom__contains=f"القاعة {numero}").first() if numero else None

    def groupe(self, bloc, code, nom_ar='', nom_fr='', **champs):
        g, _ = Groupe._base_manager.update_or_create(annee=self.annee, bloc=bloc, code=code, defaults=champs)
        # les noms ne sont posés que s'ils sont vides : un nom corrigé à la main n'est jamais écrasé
        if (nom_ar and not g.nom_ar) or (nom_fr and not g.nom_fr):
            g.nom_ar = g.nom_ar or nom_ar
            g.nom_fr = g.nom_fr or nom_fr
            g.save(update_fields=['nom_ar', 'nom_fr'])
        self.rapport['groupes'] += 1
        return g

    def affecter(self, groupe, eleve, niveau_eleve=''):
        Affectation.objects.update_or_create(etudiant=eleve, langue=groupe.langue,
                                             defaults={'groupe': groupe, 'niveau_eleve': niveau_eleve})
        self.rapport['membres'] += 1

    # ------------------------------------------------------------------------------------------------
    def importer_francais(self, nom_fichier, blocs):
        """Fichiers « Bloc Admin Pub » / « Bloc Finances » : un en-tête de groupe, puis un tableau (matricules)."""
        bloc = None
        if 'Admin' in nom_fichier:
            bloc = self.formation('الإدارة العامة')
        elif 'Finance' in nom_fichier:
            bloc = self.formation('المالية')
        courant = None
        for genre, contenu in blocs:
            if genre == 'p':
                m = re.search(r'Groupe\s*(\d+)\s*\(([^)]+)\)\s*[–—-]\s*Niveau\s*(.*)', contenu)
                if m:
                    courant = {'intitule': f"Groupe {m.group(1)}", 'code': m.group(2).strip(),
                               'niveau': re.sub(r'\s*/\s*', ' / ', re.sub(r'\s+', ' ', m.group(3))).strip(), 'prof': '', 'salle': None, 'horaire': ''}
                    continue
                if courant is None:
                    continue
                m = re.search(r'Horaire\s*:\s*([\d\s\-hH:]+?)\s*(?:Salle\s*:\s*(\d+))?\s*$', contenu)
                if m:
                    courant['horaire'] = re.sub(r'\s+', '', m.group(1))
                    courant['salle'] = m.group(2)
                m = re.match(r'Professeur\s*:\s*(.+)', contenu)
                if m:
                    courant['prof'] = m.group(1).strip()
            elif genre == 'tbl' and courant:
                num = courant['intitule'].split()[-1]
                bloc_ar, bloc_fr = ('الإدارة', 'Admin Pub') if 'Admin' in nom_fichier else ('المالية', 'Finances')
                g = self.groupe(bloc, courant['code'], nom_ar=f"المجموعة {num} - الفرنسية ({bloc_ar})",
                                nom_fr=f"Groupe {num} – Français ({bloc_fr})", langue='fr', intitule=courant['intitule'],
                                niveau_langue=courant['niveau'], professeur_texte=courant['prof'],
                                salle=self.salle(courant['salle']), horaire=courant['horaire'], actif=True)
                if courant['prof']:
                    self.rapport['professeurs'].append(f"{g.code} : {courant['prof']}")
                for ligne in contenu[1:]:
                    if len(ligne) < 3 or not ligne[1].strip().isdigit():
                        continue
                    mle, nom = ligne[1].strip(), ligne[2].strip()
                    eleve = self.par_matricule.get(mle)
                    if eleve:
                        self.affecter(g, eleve)
                    else:
                        self.rapport['introuvables'].append(f"{g.code} : matricule {mle} — {nom} (absent de la base pour {self.annee})")
                courant = None

    # ------------------------------------------------------------------------------------------------
    HINTS_FILIERE = [('مراقب خزينة', 'مراقبو الخزينة'), ('مفتش ضرائب', 'مفتشو ضرائب'),
                     ('مفتش خزينة رئيسي', 'مفتشو خزينة رئيسيون'), ('مفتش خزينة', 'مفتشو خزينة'),
                     ('قانونيين', 'قانونيون')]

    @staticmethod
    def couverture(mots_doc, mots_eleve):
        """Part des mots du nom de la liste que l'on retrouve (à une faute de frappe près) dans le nom de l'élève."""
        trouves = sum(1 for m in mots_doc if any(m == e or difflib.SequenceMatcher(None, m, e).ratio() >= 0.85 for e in mots_eleve))
        return trouves / len(mots_doc) if mots_doc else 0.0

    def rapprocher(self, nom, filiere):
        """(élève, None) si le rattachement est sûr ; (None, [suggestions]) sinon. Jamais de choix au hasard."""
        mots_doc = normaliser(nom).split()
        hint = next((v for k, v in self.HINTS_FILIERE if normaliser(k) == normaliser(filiere)), None)
        complets, approx = [], []
        for e in self.eleves:
            mots_e = normaliser(f"{e.prenom} {e.nom}").split()
            c = self.couverture(mots_doc, mots_e)
            if c == 1.0:
                complets.append(e)
            formes = [normaliser(f"{e.nom} {e.prenom}"), normaliser(f"{e.prenom} {e.nom}")]
            approx.append((max(score(normaliser(nom), f) for f in formes), e))
        if len(complets) > 1 and hint:
            complets = [e for e in complets if hint in (e.secteur.nom or '')] or complets
        if len(complets) == 1:
            return complets[0], None
        # variante d'orthographe (عثمان / عصمان…) : ressemblance très forte ET nettement meilleure que la suivante
        triés = sorted(((sc + (0.03 if hint and hint in (e.secteur.nom or '') else 0.0), e) for sc, e in approx), key=lambda x: -x[0])
        if not complets and triés[0][0] >= 0.88 and triés[0][0] - triés[1][0] >= 0.04:
            return triés[0][1], None
        pool = complets if complets else [e for _s, e in sorted(approx, key=lambda x: -x[0])[:3]]
        return None, [(dict((id(e), s) for s, e in approx).get(id(e), 0.0), e) for e in pool[:4]]

    def importer_arabe(self, nom_fichier, blocs):
        """Fichiers « Groupe A/B … » : un tableau (nom, filière, niveau) ; coordinateur et professeur en bas de page."""
        m = re.search(r'Groupe\s*([A-Za-z])', nom_fichier)
        lettre = m.group(1).upper() if m else '?'
        for genre, contenu in blocs:
            if genre == 'p':
                mm = re.match(r'Groupe\s*([A-Za-z])\s*$', contenu)
                if mm:
                    lettre = mm.group(1).upper()
        bloc = self.formation('المالية')
        coordinateur = professeur = ''
        niveaux = []
        lignes = []
        for i, (genre, contenu) in enumerate(blocs):
            if genre == 'tbl':
                lignes = [l for l in contenu[1:] if len(l) >= 3 and l[0].strip()]
            elif genre == 'p' and 'المنسق' in contenu and 'الأستاذ' in contenu and i + 1 < len(blocs) and blocs[i + 1][0] == 'p':
                morceaux = re.split(r'\s{2,}', blocs[i + 1][1].strip())
                if len(morceaux) >= 2:
                    coordinateur, professeur = morceaux[0].strip(), morceaux[-1].strip()
        niveaux = [l[2].strip() for l in lignes if l[2].strip()]
        lettre_ar = {'A': 'أ', 'B': 'ب', 'C': 'ج'}.get(lettre, lettre)
        g = self.groupe(bloc, f"G{lettre}ar", nom_ar=f"المجموعة {lettre_ar} - العربية (المالية)",
                        nom_fr=f"Groupe {lettre} – Arabe (Finances)", langue='ar', intitule=f"Groupe {lettre}",
                        niveau_langue=" – ".join(dict.fromkeys(sorted(niveaux))), professeur_texte=professeur,
                        coordinateur=coordinateur, actif=True)
        if professeur:
            self.rapport['professeurs'].append(f"{g.code} : {professeur}")
        for nom, filiere, niveau in ((l[0].strip(), l[1].strip(), l[2].strip()) for l in lignes):
            eleve, suggestions = self.rapprocher(nom, filiere)
            if eleve:
                self.affecter(g, eleve, niveau)
            elif suggestions and suggestions[0][0] >= 0.6:
                self.rapport['ambigus'].append(
                    f"{g.code} : « {nom} » ({filiere}, {niveau}) → " + " | ".join(
                        f"{e.matricule} {e.nom} {e.prenom} ({s:.2f})" for s, e in suggestions))
            else:
                self.rapport['introuvables'].append(f"{g.code} : « {nom} » ({filiere}, {niveau}) — aucun élève correspondant")
