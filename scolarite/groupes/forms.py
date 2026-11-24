from django import forms
from django.utils.translation import gettext_lazy as _

from parametres.utils import get_annee_courante
from .models import Groupe


class GroupeForm(forms.ModelForm):
    class Meta:
        model = Groupe
        fields = ['bloc', 'code', 'nom_ar', 'nom_fr', 'classe', 'langue', 'intitule', 'niveau_langue', 'professeur', 'professeur_texte',
                  'coordinateur', 'salle', 'horaire', 'actif']
        widgets = {
            'bloc': forms.Select(attrs={'class': 'form-control'}),
            'code': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'G1Ad, G2F, GAar…'}),
            'nom_ar': forms.TextInput(attrs={'class': 'form-control', 'dir': 'rtl'}),
            'nom_fr': forms.TextInput(attrs={'class': 'form-control'}),
            'classe': forms.Select(attrs={'class': 'form-control select2'}),
            'langue': forms.Select(attrs={'class': 'form-control'}),
            'intitule': forms.TextInput(attrs={'class': 'form-control'}),
            'niveau_langue': forms.TextInput(attrs={'class': 'form-control'}),
            'professeur': forms.Select(attrs={'class': 'form-control select2'}),
            'professeur_texte': forms.TextInput(attrs={'class': 'form-control'}),
            'coordinateur': forms.TextInput(attrs={'class': 'form-control'}),
            'salle': forms.Select(attrs={'class': 'form-control'}),
            'horaire': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '10-12'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['bloc'].empty_label = _("— Aucun —")
        self.fields['professeur'].empty_label = _("— Aucun —")
        self.fields['salle'].empty_label = _("— Aucune —")
        self.fields['classe'].empty_label = _("— Aucune —")
        # la langue ne change plus dès que le groupe a des élèves (la contrainte « un groupe par langue » en dépend)
        if self.instance.pk and self.instance.affectations.exists():
            self.fields['langue'].disabled = True
            self.fields['langue'].help_text = _("Le type ne peut plus être modifié : le groupe contient des élèves.")

    def clean_code(self):
        return (self.cleaned_data.get('code') or '').strip()

    def clean(self):
        data = super().clean()
        code, bloc = data.get('code'), data.get('bloc')
        if code:
            annee = self.instance.annee if self.instance.pk else get_annee_courante()
            doublon = Groupe._base_manager.filter(annee=annee, bloc=bloc, code__iexact=code).exclude(pk=self.instance.pk)
            if doublon.exists():
                self.add_error('code', _("Ce code existe déjà pour ce bloc et cette année."))
        return data
