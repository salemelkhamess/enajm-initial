from django import forms
from django.utils.translation import gettext_lazy as _
from .models import Secteur

class SecteurForm(forms.ModelForm):
    class Meta:
        model = Secteur
        fields = ['nom', 'formation']
        widgets = {
            'nom': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': _('Nom du classe'),
            }),
            'formation': forms.Select(attrs={
                'class': 'form-control select'
            }),
        }
