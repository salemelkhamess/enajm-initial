from parametres.managers import AnneeFilteredManager
from django.db import models

from etudiant.models import Etudiant
from evaluation.models import Evaluation
from trimestre.models import Trimestre
from django.utils.translation import gettext_lazy as _


class Note(models.Model):
    objects = AnneeFilteredManager('evaluation__trimestre__annee')
    class Meta:
        db_table = 'notes'

    evaluation = models.ForeignKey(Evaluation, on_delete=models.CASCADE)
    etudiant = models.ForeignKey(Etudiant, on_delete=models.CASCADE)
    note_sur_20 = models.FloatField()
    status = models.BooleanField(default=False)  # 0=False, 1=True





class NoteSpeciale(models.Model):
    objects = AnneeFilteredManager('trimestre__annee')
    NOTE_TYPE_CHOICES = [
        ('directeur', _('Note du Directeur')),
        ('etude', _("Note d'étude académique")),
        ('formation', _('Note de Formation')),
    ]
    etudiant = models.ForeignKey(Etudiant, on_delete=models.CASCADE)
    trimestre = models.ForeignKey(Trimestre, on_delete=models.CASCADE)
    type = models.CharField(max_length=20, choices=NOTE_TYPE_CHOICES)
    note = models.FloatField()

    class Meta:
        unique_together = ('etudiant', 'trimestre', 'type')

    def __str__(self):
        return f"{self.etudiant} - {_(self.get_type_display())}: {self.note}"
