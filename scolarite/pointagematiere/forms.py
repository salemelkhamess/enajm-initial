from django import forms
from django.utils.translation import gettext_lazy as _
from .models import PointageMatiere


class PointageMatiereForm(forms.ModelForm):
    # Création des choix pour les heures (de 8h à 20h par tranches de 30 minutes)
    HEURE_CHOICES = [(f"{h:02d}:{m:02d}", f"{h:02d}:{m:02d}")
                     for h in range(8, 20)
                     for m in (0, 30)]

    # Redéfinition des champs heure_debut et heure_fin
    heure_debut = forms.ChoiceField(
        choices=HEURE_CHOICES,
        widget=forms.Select(attrs={
            'class': 'form-control select',
            'style': 'width: 100%'
        }),
        label=_("Heure de début")
    )

    heure_fin = forms.ChoiceField(
        choices=HEURE_CHOICES,
        widget=forms.Select(attrs={
            'class': 'form-control select',
            'style': 'width: 100%'
        }),
        label=_("Heure de fin")
    )

    class Meta:
        model = PointageMatiere
        fields = '__all__'
        widgets = {
            'annee': forms.Select(attrs={
                'class': 'form-control select',
                'style': 'width: 100%'
            }),
            'trimestre': forms.Select(attrs={
                'class': 'form-control select',
                'style': 'width: 100%',
            }),
            'secteur': forms.Select(attrs={
                'class': 'form-control select',
                'style': 'width: 100%'
            }),
            'matiere': forms.Select(attrs={
                'class': 'form-control select',
                'style': 'width: 100%',
            }),
            'professeur': forms.Select(attrs={
                'class': 'form-control select',
                'style': 'width: 100%'
            }),
            'date_cours': forms.DateInput(attrs={
                'type': 'date',
                'class': 'form-control',
                'style': 'height: 38px'
            }),
            'contenu': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': _('Décrivez le contenu enseigné...')
            }),
            'remarques': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 2,
                'placeholder': _('Ajoutez des remarques éventuelles...')
            }),
            'etat': forms.Select(attrs={'class': 'form-control select'}),
        }
        labels = {
            'annee': _("Année"),
            'trimestre': _("Trimestre"),
            'secteur': _("Secteur"),
            'matiere': _("Matière"),
            'professeur': _("Professeur"),
            'date_cours': _("Date du cours"),
            'contenu': _("Contenu enseigné"),
            'remarques': _("Remarques"),
            'etat': _("État"),
        }

    def __init__(self, *args, **kwargs):
        self.lang = kwargs.pop('lang', None)
        super().__init__(*args, **kwargs)

        # Configuration RTL si la langue est arabe
        if self.lang == 'ar':
            for field in self.fields.values():
                field.widget.attrs['class'] = field.widget.attrs.get('class', '') + ' text-right'
                field.widget.attrs['dir'] = 'rtl'

        # Ajout de classes CSS pour les champs requis
        for field_name, field in self.fields.items():
            if field.required:
                field.widget.attrs['class'] = field.widget.attrs.get('class', '') + ' required-field'
                field.widget.attrs['style'] = field.widget.attrs.get('style', '') + ' border-left: 3px solid #f39c12;'

        # Définir les valeurs initiales si l'instance existe
        if self.instance.pk:
            self.fields['heure_debut'].initial = self.instance.heure_debut.strftime('%H:%M')
            self.fields['heure_fin'].initial = self.instance.heure_fin.strftime('%H:%M')

    def clean(self):
        cleaned_data = super().clean()
        heure_debut = cleaned_data.get('heure_debut')
        heure_fin = cleaned_data.get('heure_fin')

        if heure_debut and heure_fin:
            if heure_fin <= heure_debut:
                self.add_error('heure_fin', _("L'heure de fin doit être postérieure à l'heure de début."))

        return cleaned_data