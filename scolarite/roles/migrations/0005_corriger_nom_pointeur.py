from django.db import migrations


def corriger_nom(apps, schema_editor):
    Role = apps.get_model('roles', 'Role')
    Role.objects.filter(code='POINTEUR', name__iexact='pinter').update(name='Pointer')


class Migration(migrations.Migration):
    dependencies = [('roles', '0004_role_professeur')]
    operations = [migrations.RunPython(corriger_nom, migrations.RunPython.noop)]
