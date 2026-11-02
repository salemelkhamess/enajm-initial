from django import forms
from django.urls import reverse_lazy

from annee.models import Annee
from branches.models import Secteur
from emploie.models import EmploiDuTemps
from matiers.models import Matiere
from trimestre.models import Trimestre
from .models import PresenceEtudiant
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from django.utils.functional import lazy
from parametres.templatetags.i18n_jours import jour_i18n

_jour_label = lazy(jour_i18n, str)


def jours_choices(choices):
    """Libellés des jours traduits (arabe) au moment de l'affichage."""
    return [(value, _jour_label(label)) for value, label in choices]

class PresenceEtudiantForm(forms.ModelForm):
    class Meta:
        model = PresenceEtudiant
        fields = ['etudiant', 'matiere', 'present', 'justification', 'date_justification' , 'annee', 'trimestre', ]
        widgets = {
            'date_justification': forms.DateInput(
                attrs={'type': 'date', 'class': 'form-control'},
                format='%Y-%m-%d' )
        }
        labels = {
            'etudiant': _('Étudiant'),
            'matiere': _('Matière'),
            'present': _('Présent'),  # <-- correction ici
            'justification': _('Justification'),
            'date_justification': _('Date justification'),
            'annee': _('Annee'),
            'trimestre': _('Trimestre'),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Par défaut : aujourd'hui
        if not self.initial.get('date_justification'):
            self.initial['date_justification'] = timezone.now().date()

        # Affichage personnalisé des étudiants
        self.fields['etudiant'].label_from_instance = lambda obj: f"{obj.nom} {obj.prenom} (Matricule: {obj.matricule})"

        # Remplacement du booléen par des choix lisibles
        self.fields['present'] = forms.ChoiceField(
            choices=[(False, ('Absent')), (True, ('Présent'))],
            widget=forms.Select(attrs={'class': 'form-control select'})
        )

        # Libellé matière
        self.fields['matiere'].label_from_instance = lambda obj: f"{obj.nom}"

        # Appliquer 'form-control' à tous les champs sauf ceux déjà configurés
        for name, field in self.fields.items():
            if not isinstance(field.widget.attrs, dict):
                field.widget.attrs = {}
            field.widget.attrs.setdefault('class', 'form-control')

        self.fields['etudiant'].widget.attrs['class'] += ' select'
        self.fields['matiere'].widget.attrs['class'] += ' select'
        self.fields['present'].widget.attrs['class'] += ' select'


class PresenceFilterForm(forms.Form):
    annee = forms.ModelChoiceField(
        queryset=Annee.objects.all(),
        label=_("Année"),
        widget=forms.Select(attrs={'class': 'form-control'})
    )

    trimestre = forms.ModelChoiceField(
        queryset=Trimestre.objects.none(),
        label=_("Trimestre"),
        widget=forms.Select(attrs={'class': 'form-control'})
    )

    secteur = forms.ModelChoiceField(
        queryset=Secteur.objects.all(),
        label=_("Secteur"),
        widget=forms.Select(attrs={'class': 'form-control'})
    )

    jour = forms.ChoiceField(
        choices=jours_choices(EmploiDuTemps.JOURS_CHOIX),
        label=_("Jour"),
        widget=forms.Select(attrs={'class': 'form-control'})
    )


class PresenceForm(forms.Form):
    secteur = forms.ModelChoiceField(
        queryset=Secteur.objects.all(),
        label=_("Classe"),
        widget=forms.Select(attrs={
            'class': 'form-control select',
            'style': 'width: 100%'
        })
    )

    matiere = forms.ModelChoiceField(
        queryset=Matiere.objects.none(),  # Initialement vide
        label=_("Matière"),
        widget=forms.Select(attrs={
            'class': 'form-control select',
            'style': 'width: 100%',
        })
    )

    date_cours = forms.DateField(
        label=_("Date du cours"),
        widget=forms.DateInput(attrs={
            'type': 'date',
            'class': 'form-control datepicker',
            'style': 'width: 100%'
        })
    )

    jour = forms.ChoiceField(
        choices=jours_choices(PresenceEtudiant.JOURS_CHOIX),
        label=_("Jour"),
        widget=forms.Select(attrs={
            'class': 'form-control select',
            'style': 'width: 100%'
        })
    )



    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if 'secteur' in self.data:
            try:
                secteur_id = int(self.data.get('secteur'))
                self.fields['matiere'].queryset = Matiere.objects.filter(secteur_id=secteur_id)
            except (ValueError, TypeError):
                pass

class PresenceEtudiantForm2(forms.ModelForm):
    class Meta:
        model = PresenceEtudiant
        fields = ['present', 'justification']
        labels = {
            'present': _('Présent'),
            'justification': _('Justification')
        }


from django import forms
from django.utils.translation import gettext_lazy as _
from .models import PresenceEtudiant


class JustificationForm(forms.ModelForm):
    # Définir les choix avec traduction
    STATUS_CHOICES = (
        ('1', _('Justifié')),  # Notez que c'est une string '1'
        ('0', _('Non justifié')),  # et '0'
    )
    # Remplacer le champ status par notre version avec choix
    status = forms.ChoiceField(
        choices=STATUS_CHOICES,
        label=_('Status'),
        widget=forms.Select(attrs={
            'class': 'form-select select',
            'style': 'width: 100%',
        })
    )

    class Meta:
        model = PresenceEtudiant
        fields = ['justification', 'date_justification', 'status']
        widgets = {
            'justification': forms.Textarea(attrs={
                'rows': 3,
                'class': 'form-control',
                'style': 'background-color: #f8f9fa; border-radius: 5px; border: 1px solid #ced4da; padding: 10px;'
            }),
            'date_justification': forms.DateInput(attrs={
                'type': 'date',
                'class': 'form-control',
                'style': 'max-width: 200px; border-radius: 5px; border: 1px solid #ced4da; padding: 8px;'
            }),
        }
        labels = {
            'justification': _("Motif de l'absence"),  # Traduction du label
            'date_justification': _("Date justification"),  # Traduction du label
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Si l'instance existe et a un status, on le sélectionne par défaut
        if self.instance and self.instance.status is not None:
            self.fields['status'].initial = str(self.instance.status)


        # Appliquer des styles communs
        for field_name, field in self.fields.items():
            if field_name != 'status':  # On a déjà stylisé le status
                field.widget.attrs.update({
                    'class': 'form-control',
                    'style': 'margin-bottom: 15px; border-radius: 5px; border: 1px solid #ced4da; padding: 8px 12px; width: 100%;'
                })

            # Ajouter la classe au label
            field.label_attrs = {'class': 'form-label',
                                 'style': 'font-weight: 500; margin-bottom: 8px; display: block;'}