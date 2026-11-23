from django.db import models

from branches.models import Secteur
from formations.models import Formation


class Matiere(models.Model):
    class Meta:
        db_table = 'matiere'

    nom = models.CharField(max_length=100)
    coefficient = models.FloatField()
    secteur = models.ForeignKey(Secteur, on_delete=models.CASCADE,default=1)
    def __str__(self):
        return self.nom


def matieres_de_classe(secteur_id):
    """Matières proposées pour une classe : celles de la classe ET celles de son emploi du temps.
    (L'emploi du temps permet de choisir n'importe quelle matière : un cours peut donc être rattaché à la matière
    d'une autre classe.) Une matière de même nom n'apparaît qu'une fois, en gardant celle de l'emploi du temps."""
    from django.db.models import Q
    from emploie.models import EmploiDuTemps
    if not secteur_id:
        return Matiere.objects.none()
    ids_edt = set(EmploiDuTemps.objects.filter(secteur_id=secteur_id).values_list('matiere_id', flat=True))
    retenues = {}
    for mat in Matiere.objects.filter(Q(pk__in=ids_edt) | Q(secteur_id=secteur_id)).order_by('nom', 'id'):
        cle = ' '.join(mat.nom.split())
        if cle not in retenues or (mat.pk in ids_edt and retenues[cle].pk not in ids_edt):
            retenues[cle] = mat
    return Matiere.objects.filter(pk__in=[x.pk for x in retenues.values()]).order_by('nom')
