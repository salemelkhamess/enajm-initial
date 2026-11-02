# parametres/forms.py
from django import forms
from django.utils.translation import gettext_lazy as _
from .models import Parametres
from trimestre.models import Trimestre


class ParametresForm(forms.ModelForm):
    class Meta:
        model = Parametres
        fields = ['annee_courante', 'trimestre_courant', 'alertes_absences_actives']
        labels = {
            'annee_courante': _('Annee'),
            'trimestre_courant': _('Trimestre'),
            'alertes_absences_actives': _("Activer l'alerte d'absences"),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # CSS classes et attributs
        self.fields['annee_courante'].widget.attrs.update({
            'class': 'form-control select',
            'style': 'width: 100%;',
            'id': 'id_annee_courante'
        })

        self.fields['trimestre_courant'].widget.attrs.update({
            'class': 'form-control select',
            'style': 'width: 100%;',
            'id': 'id_trimestre_courant'
        })

        # Traduction dynamique des placeholders
        self.fields['annee_courante'].widget.attrs['placeholder'] = _('Sélectionnez une année')
        self.fields['trimestre_courant'].widget.attrs['placeholder'] = _('Sélectionnez un trimestre')

        # Filtrage des trimestres
        if 'annee_courante' in self.data:
            try:
                annee_id = int(self.data.get('annee_courante'))
                self.fields['trimestre_courant'].queryset = Trimestre.objects.filter(annee_id=annee_id)
            except (ValueError, TypeError):
                pass
        elif self.instance.pk and self.instance.annee_courante:
            self.fields['trimestre_courant'].queryset = self.instance.annee_courante.trimestre_set.all()
        else:
            self.fields['trimestre_courant'].queryset = Trimestre.objects.none()