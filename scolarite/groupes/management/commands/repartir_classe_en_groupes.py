"""
Répartit les élèves d'une classe en groupes (« sections ») de taille égale, dans l'ordre des matricules :
les N premiers dans le premier groupe, les N suivants dans le deuxième, etc.

Exemple :
  python manage.py repartir_classe_en_groupes --classe "قانونيون م أ" --codes GA,GB,GC --intitules "م أ,م ب,م ج" --taille 20 --dry-run

Un élève déjà dans une section est déplacé ; relancer la commande donne le même résultat (idempotent).
"""
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from annee.models import Annee
from branches.models import Secteur
from etudiant.models import Etudiant, ordre_matricule_croissant
from groupes.models import Affectation, Groupe
from parametres.models import Parametres


class Command(BaseCommand):
    help = "Répartit les élèves d'une classe en groupes de taille égale (ordre des matricules)."

    def add_arguments(self, parser):
        parser.add_argument('--classe', required=True, help="Nom exact de la classe")
        parser.add_argument('--codes', required=True, help="Codes des groupes, séparés par des virgules (ex. GA,GB,GC)")
        parser.add_argument('--intitules', default='', help="Intitulés des groupes (même ordre), séparés par des virgules")
        parser.add_argument('--noms-ar', default='', help="Noms arabes des groupes (même ordre), séparés par des virgules")
        parser.add_argument('--taille', type=int, default=0, help="Élèves par groupe (défaut : répartition égale)")
        parser.add_argument('--annee-id', type=int, help="Année (défaut : année active)")
        parser.add_argument('--dry-run', action='store_true', help="Simule sans rien écrire")

    def handle(self, *args, **o):
        annee = Annee.objects.get(pk=o['annee_id']) if o['annee_id'] else Parametres.get_real_instance().annee_courante
        secteur = Secteur.objects.filter(nom=o['classe']).first()
        if not secteur:
            raise CommandError(f"Classe introuvable : {o['classe']!r}")
        codes = [c.strip() for c in o['codes'].split(',') if c.strip()]
        intitules = [c.strip() for c in o['intitules'].split(',')] if o['intitules'] else []
        noms_ar = [c.strip() for c in o['noms_ar'].split(',')] if o['noms_ar'] else []
        eleves = list(Etudiant._base_manager.filter(annee=annee, secteur=secteur).order_by(*ordre_matricule_croissant()))
        if not eleves:
            raise CommandError(f"Aucun élève dans « {secteur.nom} » pour {annee}")
        taille = o['taille'] or -(-len(eleves) // len(codes))   # arrondi supérieur
        if taille * len(codes) < len(eleves):
            raise CommandError(f"{len(eleves)} élèves ne tiennent pas dans {len(codes)} groupes de {taille}")

        self.stdout.write(f"{secteur.nom} — {annee} : {len(eleves)} élèves → {len(codes)} groupes de {taille} max. ({'SIMULATION' if o['dry_run'] else 'ÉCRITURE'})")
        with transaction.atomic():
            for i, code in enumerate(codes):
                morceau = eleves[i * taille:(i + 1) * taille]
                if not morceau:
                    continue
                groupe, _ = Groupe._base_manager.update_or_create(
                    annee=annee, bloc=secteur.formation, code=code,
                    defaults={'langue': '', 'intitule': intitules[i] if i < len(intitules) else code, 'actif': True})
                if i < len(noms_ar) and not groupe.nom_ar:
                    groupe.nom_ar = noms_ar[i]
                    groupe.save(update_fields=['nom_ar'])
                if not groupe.nom_fr:
                    groupe.nom_fr = f"Section {i + 1} — {secteur.nom}"[:150] if False else f"Section {code[-1]} ({groupe.intitule})"
                    groupe.save(update_fields=['nom_fr'])
                for e in morceau:
                    Affectation.objects.update_or_create(etudiant=e, langue='', defaults={'groupe': groupe})
                self.stdout.write(f"  {code} ({groupe.intitule}) : {len(morceau)} élèves — matricules {morceau[0].matricule} → {morceau[-1].matricule}")
            if o['dry_run']:
                transaction.set_rollback(True)
