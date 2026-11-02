# forms.py
from django import forms
from .models import Formation

from django.utils.translation import gettext_lazy as _

class FormationForm(forms.ModelForm):
    class Meta:
        model = Formation
        fields = ['nom']
        widgets = {
            'nom': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Nom du secteur'}),

        },
        labels = {
            'nom': _("Nom" ),
        }


    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['nom'].widget.attrs.update({'class': 'form-control'})
