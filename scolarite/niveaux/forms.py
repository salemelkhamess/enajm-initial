from django import forms
from django.utils.translation import gettext_lazy as _

from .models import Niveau


class NiveauForm(forms.ModelForm):
    class Meta:
        model = Niveau
        fields = ['nom_fr', 'nom_ar', 'actif']
        labels = {'nom_fr': _("Nom (français)"), 'nom_ar': _("Nom (arabe)"), 'actif': _("Actif")}
        widgets = {
            'nom_fr': forms.TextInput(attrs={'class': 'form-control'}),
            'nom_ar': forms.TextInput(attrs={'class': 'form-control', 'dir': 'rtl'}),
        }

    def _clean_nom(self, champ):
        valeur = (self.cleaned_data.get(champ) or '').strip()
        existe = Niveau.objects.filter(**{f'{champ}__iexact': valeur}).exclude(pk=self.instance.pk).exists()
        if existe:
            raise forms.ValidationError(_("Un niveau porte déjà ce nom."))
        return valeur

    def clean_nom_fr(self):
        return self._clean_nom('nom_fr')

    def clean_nom_ar(self):
        return self._clean_nom('nom_ar')
