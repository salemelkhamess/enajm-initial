"""
Renseigne le nom FRANÇAIS des classes (spécialités) et des formations (blocs) existantes.
Seuls les noms français VIDES sont remplis : un nom corrigé à la main n'est jamais écrasé.
Usage : python manage.py renseigner_noms_francais [--dry-run]
"""
from django.core.management.base import BaseCommand
from django.db import transaction

from branches.models import Secteur
from formations.models import Formation

FORMATIONS = {
    'المالية': 'Finances',
    'الإدارة العامة و تدبير الشؤون العامة': 'Administration publique',
    'الدبلوماسية': 'Diplomatie',
    'القضاء و كتاب ضبط المحاكم و أعوان القضاء': 'Magistrature et greffe',
    'الصحافة و الإتصال': 'Journalisme et communication',
}

CLASSES = {
    'مراقبو الخزينة': 'Contrôleurs du Trésor',
    'الإداريون المدنيون': 'Administrateurs civils',
    'القضاة': 'Magistrats',
    'كتاب الضبط': 'Greffiers',
    'كتاب صحفيون': 'Journalistes rédacteurs',
    'مستشاروشؤون قنصلية': 'Conseillers aux affaires consulaires',
    'مراقبو الضرائب': 'Contrôleurs des impôts',
    'كتاب إدارة عامة - المالية': "Rédacteurs d'administration générale – Finances",
    'مفتشو الرقابة الاقتصادية ــ العربية': 'Inspecteurs du contrôle économique – Arabe',
    'مراقبو الرقابة الإقتصادية': 'Contrôleurs du contrôle économique',
    'كتاب إدارة عامة - الرقابة الإقتصادية': "Rédacteurs d'administration générale – Contrôle économique",
    'كتاب العدل': 'Notaires',
    'كتاب إدارة عامة - الداخلية': "Rédacteurs d'administration générale – Intérieur",
    'مستشارو مصادر بشرية': 'Conseillers en ressources humaines',
    'كتاب إدارة عامة - قسم الفرنسية': "Rédacteurs d'administration générale – Section française",
    'مفتشو الرقابة الاقتصادية ــ الفرنسية': 'Inspecteurs du contrôle économique – Français',
    'مفتشو الجمارك': 'Inspecteurs des douanes',
    'قانونيون': 'Juristes',
    'قانونيون م أ': 'Juristes – Groupe A',
    'قانونيون م ب': 'Juristes – Groupe B',
    'قانونيون م ج': 'Juristes – Groupe C',
    'مفتشو ضرائب': 'Inspecteurs des impôts',
    'محررو إدارة عامة': "Rédacteurs d'administration générale",
    'مفتشو خزينة رئيسيون': 'Inspecteurs principaux du Trésor',
}


def _cle(texte):
    return ' '.join((texte or '').split())


class Command(BaseCommand):
    help = "Renseigne les noms français des classes et des formations (uniquement s'ils sont vides)."

    def add_arguments(self, parser):
        parser.add_argument('--dry-run', action='store_true')

    def handle(self, *args, **o):
        n = 0
        inconnus = []
        with transaction.atomic():
            for modele, table in ((Formation, FORMATIONS), (Secteur, CLASSES)):
                dico = {_cle(k): v for k, v in table.items()}
                for obj in modele.objects.all():
                    fr = dico.get(_cle(obj.nom))
                    if not fr:
                        inconnus.append(f"{modele.__name__} {obj.pk} : {obj.nom}")
                    elif not obj.nom_fr:
                        obj.nom_fr = fr
                        obj.save(update_fields=['nom_fr'])
                        n += 1
                        self.stdout.write(f"  {obj.nom}  →  {fr}")
            if o['dry_run']:
                transaction.set_rollback(True)
        self.stdout.write(self.style.SUCCESS(f"{n} nom(s) français renseigné(s){' (simulation)' if o['dry_run'] else ''}."))
        for i in inconnus:
            self.stdout.write(self.style.WARNING(f"Sans traduction : {i}"))
