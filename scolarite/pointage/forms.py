from django import forms
from .models import Pointage
from emploie.models import EmploiDuTemps
from branches.models import Secteur

class PointageForm(forms.ModelForm):
    JOUR_CHOICES = [('', '')] + [
        ('Lundi', 'Lundi'),
        ('Mardi', 'Mardi'),
        ('Mercredi', 'Mercredi'),
        ('Jeudi', 'Jeudi'),
        ('Vendredi', 'Vendredi'),
        ('Samedi', 'Samedi'),
    ]

    secteur = forms.ModelChoiceField(
        queryset=Secteur.objects.all(),
        required=True,
        widget=forms.Select(attrs={'class': 'form-control select'})
    )
    jour = forms.ChoiceField(
        choices=JOUR_CHOICES,
        required=True,
        widget=forms.Select(attrs={'class': 'form-control select'})
    )
    # Dans votre forms.py
    date = forms.DateField(
        widget=forms.DateInput(
            attrs={
                'class': 'form-control datepicker',
                'autocomplete': 'off'
            },
            format='%Y-%m-%d'
        ),
        input_formats=['%Y-%m-%d']
    )

    labels = {
        'secteur': 'Departement',
    }

    class Meta:
        model = Pointage
        fields = ['secteur', 'jour', 'date']
        widgets = {
            'date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
        }
        labels = {
            'secteur': 'Departement',
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['seance'] = forms.ModelChoiceField(
            queryset=EmploiDuTemps.objects.none(),
            required=False,
            widget=forms.Select(attrs={'class': 'form-control'})
        )