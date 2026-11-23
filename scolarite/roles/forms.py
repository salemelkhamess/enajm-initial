from django import forms

import roles
import users
from .models import  Role
from django.utils.translation import gettext_lazy as _


class RoleForm(forms.ModelForm):
    class Meta:
        model = Role
        fields = ['code', 'name', 'description']
        widgets = {
            'description': forms.Textarea(attrs={'rows': 3}),
        }



class UserCreationForm(forms.ModelForm):
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={'class': 'form-control'}),
        label=_("Mot de passe")
    )
    roles = forms.ModelMultipleChoiceField(
        queryset=Role.visibles(),
        widget=forms.CheckboxSelectMultiple,
        required=False,
        label=_("Rôles")
    )

    birth_date = forms.DateField(
        widget=forms.DateInput(attrs={
            'type': 'date',
            'class': 'form-control'
        }),
        required=False,
        label=_("Date de naissance")
    )

    class Meta:
        model = users.models.User
        fields = ['first_name', 'last_name', 'email', 'phone', 'address', 'birth_date', 'password', 'roles']
        labels = {
            'first_name': _("Prénom"),
            'last_name': _("Nom"),
            'email': _("Adresse email"),
            'phone': _("Téléphone"),
            'address': _("Adresse"),
        }
        error_messages = {
            'email': {'unique': _("Un utilisateur avec cet email existe déjà."), 'invalid': _("Saisissez une adresse email valide."),
                      'required': _("L'adresse email est obligatoire.")},
            'first_name': {'required': _("Le prénom est obligatoire.")},
            'last_name': {'required': _("Le nom est obligatoire.")},
        }
        widgets = {
            'first_name': forms.TextInput(attrs={'class': 'form-control'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'phone': forms.TextInput(attrs={'class': 'form-control'}),
            'address': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['roles'].label_from_instance = lambda role: role.libelle

    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data['password'])  # Hash du mot de passe
        if commit:
            user.save()
            # Assigner les rôles
            user_roles = self.cleaned_data['roles']
            for role in user_roles:
                user.add_role(role.code)
        return user


class UserUpdateForm(forms.ModelForm):
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={'class': 'form-control'}),
        label=_("Nouveau mot de passe"),
        required=False
    )

    roles = forms.ModelMultipleChoiceField(
        queryset=Role.visibles(),
        widget=forms.CheckboxSelectMultiple,
        required=False,
        label=_("Rôles")
    )

    birth_date = forms.DateField(
        widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
        required=False,
        label=_("Date de naissance")
    )

    class Meta:
        model = users.models.User
        fields = ['first_name', 'last_name', 'email', 'phone', 'address', 'birth_date', 'password', 'roles']
        labels = {
            'first_name': _("Prénom"),
            'last_name': _("Nom"),
            'email': _("Adresse email"),
            'phone': _("Téléphone"),
            'address': _("Adresse"),
        }
        error_messages = {
            'email': {'unique': _("Un utilisateur avec cet email existe déjà."), 'invalid': _("Saisissez une adresse email valide."),
                      'required': _("L'adresse email est obligatoire.")},
            'first_name': {'required': _("Le prénom est obligatoire.")},
            'last_name': {'required': _("Le nom est obligatoire.")},
        }
        widgets = {
            'first_name': forms.TextInput(attrs={'class': 'form-control'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'phone': forms.TextInput(attrs={'class': 'form-control'}),
            'address': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['roles'].label_from_instance = lambda role: role.libelle
        # Pré-remplir les rôles existants (les rôles masqués ne sont pas affichés)
        if self.instance and self.instance.pk:
            self.fields['roles'].initial = [ur.role for ur in self.instance.user_roles.filter(is_active=True)
                                            if not ur.role.masque]

    def save(self, commit=True):
        user = super().save(commit=False)
        password = self.cleaned_data.get('password')
        if password:
            user.set_password(password)

        if commit:
            user.save()

            # Supprimer les rôles existants, sauf les rôles masqués (non modifiables ici : ils restent attribués)
            user.user_roles.exclude(role__code__in=Role.ROLES_MASQUES).delete()

            # Ajouter les rôles sélectionnés
            for role in self.cleaned_data.get('roles', []):
                user.add_role(role.code)

        return user
