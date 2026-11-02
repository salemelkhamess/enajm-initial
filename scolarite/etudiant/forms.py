from django import forms
from django.utils.translation import gettext_lazy as _
from .models import Etudiant


class EtudiantForm(forms.ModelForm):
    # Champ pour les diplômes (multiple choice)
    diplomes = forms.MultipleChoiceField(
        choices=Etudiant.DIPLOME_CHOICES,
        required=False,
        widget=forms.CheckboxSelectMultiple,
        label=_("Diplômes")
    )

    class Meta:
        model = Etudiant
        fields = [
            'nni', 'matricule', 'nom', 'prenom', 'date_naissance',
            'lieu_naissance', 'sexe', 'telephone', 'email', 'photo',
            'secteur', 'annee', 'situation_amoureuse', 'diplomes', 'nombre_enfants'
        ]

        widgets = {
            'date_naissance': forms.NumberInput(attrs={
                'min': 1900,
                'max': 2100,
                'placeholder': 'Date de naissance'
            }),            'sexe': forms.Select(choices=Etudiant.SEXE_CHOICES),
            'situation_amoureuse': forms.Select(choices=Etudiant.SITUATION_AMOUREUSE_CHOICES),
            'photo': forms.ClearableFileInput(),
            'secteur': forms.Select(attrs={'class': 'form-control select'}),
            'annee': forms.Select(attrs={'class': 'form-control select'}),
            'nombre_enfants': forms.NumberInput(attrs={'min': 0}),
        }

        labels = {
            'secteur': _('Département'),
            'nni': _('NNI'),
            'date_naissance': _('Date de naissance'),
            'lieu_naissance': _('Lieu de naissance'),
            'sexe': _('Sexe'),
            'telephone': _('Téléphone'),
            'email': _('Email'),
            'photo': _('Photo'),
            'situation_amoureuse': _('Situation amoureuse'),
            'nombre_enfants': _("Nombre d'enfants"),
        }

    def __init__(self, *args, **kwargs):
        super(EtudiantForm, self).__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs['class'] = 'form-control'
            # Ne pas rendre tous les champs obligatoires
            self.fields['prenom'].required = False

            if field.required:
                field.widget.attrs['required'] = 'required'

        # Exceptions pour les widgets spéciaux
        self.fields['secteur'].widget.attrs['class'] += ' select'
        self.fields['annee'].widget.attrs['class'] += ' select'
        self.fields['situation_amoureuse'].widget.attrs['class'] += ' select'
        self.fields['diplomes'].widget.attrs['class'] = ''