from django import forms
from django.contrib.auth.forms import PasswordChangeForm
from django.contrib.auth.models import User, Group
from django.core.exceptions import ValidationError
from django.contrib.auth.models import Group, Permission
from django.utils.translation import gettext_lazy as _
from  users import models

class UserForm(forms.ModelForm):
    password = forms.CharField(widget=forms.PasswordInput(attrs={'class': 'form-control'}), label="Mot de passe")
    password_confirm = forms.CharField(widget=forms.PasswordInput(attrs={'class': 'form-control'}), label="Confirmer le mot de passe")
    group = forms.ModelChoiceField(
        queryset=Group.objects.all(),
        required=True,
        label="Groupe",
        widget=forms.Select(attrs={'class': 'form-control select'})
    )

    class Meta:
        model = User
        fields = ['username', 'email']

        widgets = {
            'username': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
        }


    def clean_password_confirm(self):
        password = self.cleaned_data.get('password')
        password_confirm = self.cleaned_data.get('password_confirm')
        if password and password_confirm and password != password_confirm:
            raise ValidationError("Les mots de passe ne correspondent pas.")
        return password_confirm

    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data["password"])
        if commit:
            user.save()
            group = self.cleaned_data["group"]
            user.groups.add(group)  # affecte le groupe
        return user




class GroupForm(forms.ModelForm):
    permissions = forms.ModelMultipleChoiceField(
        queryset=Permission.objects.all(),
        required=False,
        widget=forms.CheckboxSelectMultiple(attrs={'class': 'form-check'}),
        label="Permissions"
    )

    class Meta:
        model = Group
        fields = ['name', 'permissions']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control '}),
        }


    def save(self, commit=True):
        group = super().save(commit=False)
        if commit:
            group.save()
            group.permissions.set(self.cleaned_data['permissions'])  # Assigner les permissions
        return group


class UserProfileForm(forms.ModelForm):
    class Meta:
        model = models.User
        fields = ['email', 'first_name', 'last_name', 'phone', 'address', 'birth_date']
        widgets = {
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'first_name': forms.TextInput(attrs={'class': 'form-control'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control'}),
            'phone': forms.TextInput(attrs={'class': 'form-control'}),
            'address': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3
            }),
            'birth_date': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date'
            }),
        }
        labels = {
            'email': _('Adresse email'),
            'first_name': _('Prénom'),
            'last_name': _('Nom'),
            'phone': _('Téléphone'),
            'address': _('Adresse'),
            'birth_date': _('Date de naissance'),
        }
        help_texts = {
            'email': _('Votre adresse email principale'),
        }
        error_messages = {
            'email': {
                'unique': _('Cette adresse email est déjà utilisée.'),
            },
        }


class NoValidationPasswordChangeForm(forms.Form):
    old_password = forms.CharField(
        label=_("Ancien mot de passe"),
        strip=False,
        widget=forms.PasswordInput(attrs={'autocomplete': 'current-password', 'class': 'form-control'}),
    )
    new_password1 = forms.CharField(
        label=_("Nouveau mot de passe"),
        widget=forms.PasswordInput(attrs={'autocomplete': 'new-password', 'class': 'form-control'}),
        strip=False,
    )
    new_password2 = forms.CharField(
        label=_("Confirmation du nouveau mot de passe"),
        strip=False,
        widget=forms.PasswordInput(attrs={'autocomplete': 'new-password', 'class': 'form-control'}),
    )

    def __init__(self, user, *args, **kwargs):
        self.user = user
        super().__init__(*args, **kwargs)

    def clean(self):
        cleaned_data = super().clean()
        new_password1 = cleaned_data.get("new_password1")
        new_password2 = cleaned_data.get("new_password2")

        if new_password1 and new_password2 and new_password1 != new_password2:
            raise forms.ValidationError(
                _("Les deux mots de passe ne correspondent pas."),
                code='password_mismatch',
            )

        return cleaned_data

    def save(self, commit=True):
        password = self.cleaned_data["new_password1"]
        self.user.set_password(password)
        if commit:
            self.user.save()
        return self.user