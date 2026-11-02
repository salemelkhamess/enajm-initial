from django.db import models

class Formation(models.Model):
    class Meta:
        db_table = 'formations'

    nom = models.CharField(max_length=100)

    def __str__(self):
        return self.nom