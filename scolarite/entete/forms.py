from django import forms

from entete.models import Entete

class EnteteForm(forms.ModelForm):
    class Meta:
        model = Entete
        fields = '__all__'

    def __init__(self, *args, **kwargs):
        super(EnteteForm, self).__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs['class'] = 'form-control'
