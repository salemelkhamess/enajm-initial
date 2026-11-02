from django import forms
from django.utils.translation import gettext_lazy as _
from .models import Matiere

class MatiereForm(forms.ModelForm):
    class Meta:
        model = Matiere
        fields = ['nom', 'coefficient', 'secteur']
        labels = {
            'nom': _('Nom'),
            'coefficient': _('Coefficient'),
            'formation': _('Département'),  # Remarque: si tu veux ce champ dans le form
            'secteur': _('Classe'),
        }

    def __init__(self, *args, **kwargs):
        super(MatiereForm, self).__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs['class'] = 'form-control'
            field.widget.attrs['required'] = 'required'
