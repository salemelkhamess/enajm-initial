from django import forms
import datetime

from .models import PresenceProfesseur

class PresenceProfesseurForm(forms.ModelForm):
    class Meta:
        model = PresenceProfesseur
        fields = '__all__'
        widgets = {
            'present': forms.Select(choices=[ (False, 'Absent') , (True, 'Présent')]),
            'date_justification': forms.DateInput(attrs={'type': 'date'}),
        }


    def __init__(self, *args, **kwargs):
        super(PresenceProfesseurForm, self).__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs['class'] = 'form-control'
        self.fields['professeur'].widget.attrs['class'] += ' select'
        self.fields['matiere'].widget.attrs['class'] += ' select'
        self.fields['present'].widget.attrs['class'] += ' select'




        # 🗓️ Définir la date d'aujourd'hui si le champ est vide (création uniquement)
        if not self.instance.pk:
            self.fields['date_justification'].initial = datetime.date.today()