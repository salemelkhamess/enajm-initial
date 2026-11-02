from django import forms
from .models import Trimestre

from django.utils.translation import gettext_lazy as _
from .models import Trimestre

class TrimestreForm(forms.ModelForm):
    class Meta:
        model = Trimestre
        fields = '__all__'
        labels = {
            'annee': _("Année"),
            'numero_trimestre': _("Numéro"),
            'debut': _("Début"),
            'fin': _("Fin"),
            'nom_fr': _("Nom (Français)"),
            'nom_ar': _("Nom (Arabe)"),
        }
        widgets = {
            'debut': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'fin': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
        }

    def __init__(self, *args, **kwargs):
        super(TrimestreForm, self).__init__(*args, **kwargs)
        for field in self.fields:
            if field not in ['debut', 'fin']:
                self.fields[field].widget.attrs['class'] = 'form-control'
        self.fields['annee'].widget.attrs['class'] += ' select'

