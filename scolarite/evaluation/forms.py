from django import forms
from django.utils.translation import gettext_lazy as _
from .models import Evaluation

class EvaluationForm(forms.ModelForm):
    class Meta:
        model = Evaluation
        fields = '__all__'
        widgets = {
            'date': forms.DateInput(
                attrs={'type': 'date', 'class': 'form-control'}
            ),
            'type': forms.Select(choices=Evaluation.TYPE_CHOICES)
        }
        labels = {
            'matiere': _('Matière'),
            'type': _('Type évaluation'),
            'date': _('Date'),
            'coefficient': _('Coefficient'),
            'trimestre': _('Trimestre'),
            'secteur': _('Classe'),
        }

    def __init__(self, *args, **kwargs):
        super(EvaluationForm, self).__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs['class'] = 'form-control'
        self.fields['matiere'].widget.attrs['class'] += ' select'
        self.fields['type'].widget.attrs['class'] += ' select'
        self.fields['trimestre'].widget.attrs['class'] += ' select'
        self.fields['secteur'].widget.attrs['class'] += ' select'
