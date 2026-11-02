from parametres.managers import AnneeFilteredManager
from django.db import models
from django.utils.translation import gettext_lazy as _
from etudiant.models import Etudiant

class DocumentEtudiant(models.Model):
    objects = AnneeFilteredManager('etudiant__annee')
    TYPES_DOCUMENT = [
        ('DN', _('Diplôme National')),
        ('AT', _('Attestation')),
        ('RE', _('Relevé de Notes')),
        ('AU', _('Autre')),
    ]

    etudiant = models.ForeignKey(
        Etudiant,
        on_delete=models.CASCADE,
        related_name='documents',
        verbose_name=_("Étudiant")
    )
    type_document = models.CharField(
        max_length=2,
        choices=TYPES_DOCUMENT,
        verbose_name=_("Type de document")
    )
    fichier = models.FileField(
        upload_to='documents/etudiants/',
        verbose_name=_("Fichier")
    )
    date_upload = models.DateTimeField(
        auto_now_add=True,
        verbose_name=_("Date d'upload")
    )
    description = models.TextField(
        blank=True,
        null=True,

        verbose_name=_("Description")
    )

    class Meta:
        verbose_name = _("Document d'étudiant")
        verbose_name_plural = _("Documents des étudiants")
        ordering = ['-date_upload']

    def __str__(self):
        return f"{self.get_type_document_display()} - {self.etudiant}"