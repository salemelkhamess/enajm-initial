from django import forms
from .models import Salle

class SalleForm(forms.ModelForm):
    class Meta:
        model = Salle
        fields = ['nom', 'capacite', 'description']

    def __init__(self, *args, **kwargs):
        super(SalleForm, self).__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs.update({'class': 'form-control'})
