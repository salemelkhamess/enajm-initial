from django import forms
from django.utils.translation import gettext_lazy as _
from .models import Secteur

class SecteurForm(forms.ModelForm):
    class Meta:
        model = Secteur
        fields = ['nom', 'nom_fr', 'formation']
        widgets = {
            'nom': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': _('Nom du classe'),
            }),
            'nom_fr': forms.TextInput(attrs={'class': 'form-control', 'placeholder': _('Nom en français')}),
            'formation': forms.Select(attrs={
                'class': 'form-control select'
            }),
        }
