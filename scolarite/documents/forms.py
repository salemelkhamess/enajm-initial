from django import forms
from .models import DocumentEtudiant
from django.utils.translation import gettext_lazy as _

class DocumentForm(forms.ModelForm):
    class Meta:
        model = DocumentEtudiant
        fields = ['type_document', 'fichier', 'description']
        widgets = {
            'type_document': forms.Select(attrs={
                'class': 'form-select select mb-3',
                'style': 'width: 100%;'
            }),
            'fichier': forms.FileInput(attrs={
                'class': 'form-control mb-3',
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-control mb-3',
                'rows': 3,
                'placeholder': ''
            }),
        }
        labels = {
            'type_document': _("Type de document"),
            'fichier': _("Fichier"),
            'description': _("Description")
        }