from django import forms
from django.utils.translation import gettext_lazy as _
from .models import Annee

class AnneeForm(forms.ModelForm):
    class Meta:
        model = Annee
        fields = ['formation', 'numero_annee']
        labels = {
            'formation': _('formation'),
            'numero_annee': _('numero_annee'),
        }

    def __init__(self, *args, **kwargs):
        super(AnneeForm, self).__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs['class'] = 'form-control'
        self.fields['formation'].widget.attrs['class'] += ' select'

    def clean_numero_annee(self):
        numero = self.cleaned_data.get('numero_annee')
        if numero <= 0:
            raise forms.ValidationError(_("Le numéro de l'année doit être supérieur à 0."))
        return numero