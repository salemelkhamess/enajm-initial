# forms.py
from django import forms

from annee.models import Annee
from branches.models import Secteur
from etudiant.models import Etudiant
from trimestre.models import Trimestre
from .models import Note
from django.utils.translation import gettext_lazy as _


class NoteForm(forms.ModelForm):
    class Meta:
        model = Note
        fields = '__all__'

    def __init__(self, *args, **kwargs):
        super(NoteForm, self).__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs['class'] = 'form-control'


class BulletinForm(forms.Form):
    annee = forms.ModelChoiceField(
        queryset=Annee.objects.all(),
        label=_("Année"),
        widget=forms.Select(attrs={'class': 'form-control select'})
    )

    trimestre = forms.ModelChoiceField(
        queryset=Trimestre.objects.all(),
        label=_("Trimestre"),
        widget=forms.Select(attrs={'class': 'form-control select'})
    )

    secteur = forms.ModelChoiceField(
        queryset=Secteur.objects.all(),
        label=_("Secteur"),
        widget=forms.Select(attrs={'class': 'form-control select'})
    )

    type_evaluation = forms.ChoiceField(
        choices=[('devoir', _('Devoir')), ('examen', _('Examen'))],
        label=_("Type d'évaluation"),
        initial='examen',  # Valeur par défaut
        widget=forms.Select(attrs={'class': 'form-control select'})
    )

    def __init__(self, *args, **kwargs):
        super(BulletinForm, self).__init__(*args, **kwargs)

        # Optionnel: Ordonner les queryset si nécessaire
        self.fields['annee'].queryset = Annee.objects.all().order_by('-numero_annee')
        self.fields['trimestre'].queryset = Trimestre.objects.all().order_by('numero_trimestre')
        self.fields['secteur'].queryset = Secteur.objects.all().order_by('nom')



