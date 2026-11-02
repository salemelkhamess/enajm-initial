from django import forms
from matiers.models import Matiere
from .models import PV
from django.utils.translation import gettext_lazy as _
from annee.models import Annee
from trimestre.models import Trimestre


class PVForm(forms.ModelForm):
    class Meta:
        model = PV
        fields = [
            'etudiant',
            'type',
            'matiere',
            'annee',
            'trimestre',
            'jour_semaine',
            'date_incident',
            'contenu'
        ]
        widgets = {
            'date_incident': forms.DateInput(attrs={'type': 'date'}),
        }

    def __init__(self, *args, **kwargs):
        current_user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)

        # Configuration de base pour tous les champs
        for field in self.fields.values():
            field.widget.attrs['class'] = 'form-control'

        # Configuration spécifique pour chaque champ
        select_fields = ['etudiant', 'type', 'annee', 'trimestre', 'jour_semaine', 'matiere']
        for field in select_fields:
            self.fields[field].widget.attrs['class'] += ' select'

        # Personnalisation des labels
        self.fields['type'].label = _("Type de PV")
        self.fields['etudiant'].label = _("Étudiant")
        self.fields['matiere'].label = _("Matière")
        self.fields['annee'].label = _("Annee")
        self.fields['trimestre'].label = _("Trimestre")
        self.fields['jour_semaine'].label = _("Jour")
        self.fields['date_incident'].label = _("Date")
        self.fields['contenu'].label = _("Description")

        # Configuration supplémentaire
        self.fields['contenu'].widget.attrs['rows'] = 4
        self.fields['contenu'].widget.attrs['placeholder'] = _("Décrivez en détail l'incident...")

        # Filtrage des querysets
        self.fields['annee'].queryset = Annee.objects.all().order_by('-numero_annee')
        self.fields['trimestre'].queryset = Trimestre.objects.all().order_by('numero_trimestre')

        # CORRECTION: Set the queryset for matiere field properly
        self.fields['matiere'].queryset = Matiere.objects.all()

        # Si vous voulez rendre certains champs obligatoires
        required_fields = ['annee', 'trimestre', 'date_incident', 'matiere']
        for field in required_fields:
            self.fields[field].required = True

    def clean(self):
        cleaned_data = super().clean()
        date_incident = cleaned_data.get('date_incident')
        jour_semaine = cleaned_data.get('jour_semaine')

        # Validation cohérence date/jour de semaine
        if date_incident and not jour_semaine:
            jours = ['Lundi', 'Mardi', 'Mercredi', 'Jeudi', 'Vendredi', 'Samedi', 'Dimanche']
            jour_index = date_incident.weekday()
            if jour_index < len(jours):
                cleaned_data['jour_semaine'] = jours[jour_index]

        return cleaned_data