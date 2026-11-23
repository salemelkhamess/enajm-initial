from django.db import migrations


def marquer_acceptees(apps, schema_editor):
    """Les absences déjà justifiées avant cette évolution sont considérées comme acceptées."""
    Presence = apps.get_model('presenceetudiant', 'PresenceEtudiant')
    Presence.objects.filter(is_justified=True).update(justif_etat='acceptee')


class Migration(migrations.Migration):
    dependencies = [('presenceetudiant', '0008_presenceetudiant_justif_decidee_le_and_more')]
    operations = [migrations.RunPython(marquer_acceptees, migrations.RunPython.noop)]
