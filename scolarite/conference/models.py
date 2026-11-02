from django.db import models

class Conference(models.Model):
    class Meta:
        db_table = 'conferences'
    titre = models.CharField(max_length=200)
    date = models.DateField()
    heure_debut = models.TimeField()
    heure_fin = models.TimeField()
    lieu = models.CharField(max_length=100)