# forms.py
from django import forms
from .models import Formation

from django.utils.translation import gettext_lazy as _

class FormationForm(forms.ModelForm):
    class Meta:
        model = Formation
        fields = ['nom', 'nom_fr']
        widgets = {
            'nom': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Nom du secteur'}),

        },
        labels = {
            'nom': _("Nom" ),
        }


    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['nom'].widget.attrs.update({'class': 'form-control'})
        if 'nom_fr' in self.fields:
            self.fields['nom_fr'].widget.attrs.update({'class': 'form-control', 'placeholder': 'Nom en français'})
