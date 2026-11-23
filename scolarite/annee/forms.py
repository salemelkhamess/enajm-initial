from django import forms
from django.utils.translation import gettext_lazy as _
from .models import Annee


class AnneeForm(forms.ModelForm):
    """Une année est créée une seule fois, pour tous les départements."""

    class Meta:
        model = Annee
        fields = ['numero_annee']
        labels = {'numero_annee': _('numero_annee')}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs['class'] = 'form-control'

    def clean_numero_annee(self):
        numero = self.cleaned_data.get('numero_annee')
        if numero is None or numero <= 0:
            raise forms.ValidationError(_("Le numéro de l'année doit être supérieur à 0."))
        if Annee.objects.filter(numero_annee=numero).exclude(pk=self.instance.pk).exists():
            raise forms.ValidationError(_("Cette année existe déjà."))
        return numero
