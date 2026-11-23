from django.db import migrations


def annees_globales(apps, schema_editor):
    """Les années existantes deviennent valables pour tous les départements (le département n'était pas utilisé)."""
    Annee = apps.get_model('annee', 'Annee')
    Annee.objects.update(formation=None)


class Migration(migrations.Migration):
    dependencies = [('annee', '0002_alter_annee_formation')]
    operations = [migrations.RunPython(annees_globales, migrations.RunPython.noop)]
