# forms.py
from django import forms
from .models import Professeur
from django.utils.translation import gettext_lazy as _


class ProfesseurForm(forms.ModelForm):
    class Meta:
        model = Professeur
        fields = '__all__'
        labels = {
            'nom': _("Nom"),
            'prenom': _("Prénom"),
            'email': _("Email"),
            'telephone': _("Téléphone"),
            'specialite': _("NNI"),
        }

    def __init__(self, *args, **kwargs):
        super(ProfesseurForm, self).__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs['class'] = 'form-control'
        if 'user' in self.fields:
            self.fields['user'].required = False
            self.fields['user'].label = _("Compte utilisateur (rôle Professeur)")
