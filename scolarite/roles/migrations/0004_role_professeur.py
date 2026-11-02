from django.db import migrations


def creer_role_professeur(apps, schema_editor):
    Role = apps.get_model('roles', 'Role')
    Role.objects.get_or_create(
        code='PROFESSEUR',
        defaults={'name': 'Professeur',
                  'description': "Enregistre les absences, sa présence, le contenu enseigné et les notes de ses matières."},
    )


class Migration(migrations.Migration):
    dependencies = [('roles', '0003_alter_role_code')]
    operations = [migrations.RunPython(creer_role_professeur, migrations.RunPython.noop)]
