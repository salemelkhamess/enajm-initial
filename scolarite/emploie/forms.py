from django import forms

from annee.models import Annee
from branches.models import Secteur
from trimestre.models import Trimestre
from .models import EmploiDuTemps
from django.core.exceptions import ValidationError
from django.db.models import Q
from datetime import time
from django.utils.translation import gettext_lazy as _


# Liste des heures par pas de 30 minutes
HEURE_CHOICES = [
    (f"{h:02d}:{m:02d}", f"{h:02d}:{m:02d}")
    for h in range(8, 19)
    for m in (0, 30)
]


class EmploiDuTempsForm(forms.ModelForm):
    heure_debut = forms.ChoiceField(choices=HEURE_CHOICES, widget=forms.Select(attrs={'class': 'form-control'}))
    heure_fin = forms.ChoiceField(choices=HEURE_CHOICES, widget=forms.Select(attrs={'class': 'form-control'}))

    class Meta:
        model = EmploiDuTemps
        fields = ['annee', 'trimestre', 'niveau', 'langue', 'secteur', 'matiere', 'professeur', 'salle', 'jour', 'heure_debut', 'heure_fin']

        labels = {
            'secteur': _("Département"),
            'niveau': _("Niveau (cours transversal)"),
            'langue': _("Langue du cours"),
            'annee': _("Année"),
            'trimestre': _("Trimestre"),
            'matiere': _("Matière"),
            'professeur': _("Professeur"),
            'salle': _("Salle"),
            'jour': _("Jour"),
        }
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        from presenceetudiant.forms import jours_choices
        self.fields['jour'].choices = [('', '---------')] + jours_choices(EmploiDuTemps.JOURS_CHOIX)

        # Niveau (facultatif) : seulement les niveaux actifs (+ celui du cours modifié) ; le secteur devient facultatif
        from niveaux.models import Niveau
        niveaux = Niveau.objects.filter(Q(actif=True) | Q(pk=self.instance.niveau_id)) if self.instance.pk and self.instance.niveau_id else Niveau.actifs()
        self.fields['niveau'].queryset = niveaux
        self.fields['niveau'].required = False
        self.fields['niveau'].label_from_instance = lambda n: n.libelle
        self.fields['langue'].required = False
        self.fields['langue'].choices = [('', '---------')] + EmploiDuTemps.LANGUES
        self.fields['secteur'].required = False

        # Configuration des attributs des champs
        for name, field in self.fields.items():
            classes = 'form-control'
            if field.widget.input_type == 'select':
                classes += ' select'  # classe select2 à appliquer au JS
            field.widget.attrs.update({'class': classes})

    def clean(self):
        cleaned_data = super().clean()
        niveau = cleaned_data.get('niveau')
        if niveau:
            # cours par niveau : langue obligatoire, secteur = secteur de rattachement de la matière
            if not cleaned_data.get('langue'):
                self.add_error('langue', _("Choisissez la langue du cours (arabe ou français)."))
            matiere = cleaned_data.get('matiere')
            if matiere:
                cleaned_data['secteur'] = matiere.secteur
        else:
            cleaned_data['langue'] = ''
            if not cleaned_data.get('secteur'):
                self.add_error('secteur', _("Ce champ est obligatoire (sauf pour un cours par niveau)."))
        annee = cleaned_data.get('annee')
        trimestre = cleaned_data.get('trimestre')
        secteur = cleaned_data.get('secteur')
        salle = cleaned_data.get('salle')
        professeur = cleaned_data.get('professeur')
        jour = cleaned_data.get('jour')
        heure_debut = cleaned_data.get('heure_debut')
        heure_fin = cleaned_data.get('heure_fin')

        if not all([annee, trimestre, secteur, salle, professeur, jour, heure_debut, heure_fin]):
            return cleaned_data

        # Vérifier que le trimestre appartient à l'année
        if trimestre.annee != annee:
            raise ValidationError(_("Le trimestre sélectionné n'appartient pas à l'année choisie."))

        # Convertir les heures en objets time pour la comparaison
        try:
            hd = time.fromisoformat(heure_debut)
            hf = time.fromisoformat(heure_fin)
        except (ValueError, AttributeError):
            return cleaned_data

        # Vérifier que l'heure de fin est après l'heure de début
        if hf <= hd:
            raise ValidationError(_("L'heure de fin doit être après l'heure de début."))

        # Une même salle peut accueillir plusieurs cours au même créneau (cours commun à plusieurs classes)

        # Un professeur peut avoir plusieurs cours au même créneau (cours communs, classes regroupées) : pas de contrôle.

        return cleaned_data


class EmploiParametresForm(forms.Form):
    annee = forms.ModelChoiceField(
        queryset=Annee.objects.all(),
        widget=forms.Select(attrs={'class': 'form-control'}),
        label=_("Annee")  # <-- à traduire

    )
    trimestre = forms.ModelChoiceField(
        queryset=Trimestre.objects.none(),
        widget=forms.Select(attrs={'class': 'form-control'}),
        label=_("Trimestre")  # <-- à traduire

    )
    secteur = forms.ModelChoiceField(
        queryset=Secteur.objects.all(),
        widget=forms.Select(attrs={
            'class': 'form-control',
            'id': 'id_secteur'
        }),
        label=_("Classe")  # <-- à traduire

    )


    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        if 'annee' in self.data:
            try:
                annee_id = int(self.data.get('annee'))
                self.fields['trimestre'].queryset = Trimestre.objects.filter(annee_id=annee_id)
            except (ValueError, TypeError):
                pass
        elif self.initial.get('annee'):
            self.fields['trimestre'].queryset = Trimestre.objects.filter(annee_id=self.initial['annee'].id)