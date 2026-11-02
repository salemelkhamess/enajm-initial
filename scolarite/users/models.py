from django.db import models
from django.contrib.auth.models import AbstractUser
from django.core.validators import EmailValidator

from roles.models import UserRole, Role
from users.managers import CustomUserManager


class User(AbstractUser):
    username = None  # <-- on désactive le champ username
    email = models.EmailField(
        unique=True,
        validators=[EmailValidator()],
        verbose_name="Adresse email",
        error_messages={'unique': "Un utilisateur avec cet email existe déjà."}
    )
    first_name = models.CharField(max_length=30, verbose_name="Prénom")
    last_name = models.CharField(max_length=150, verbose_name="Nom")
    phone = models.CharField(max_length=20, blank=True, null=True, verbose_name="Téléphone")
    address = models.TextField(blank=True, null=True, verbose_name="Adresse")
    birth_date = models.DateField(blank=True, null=True, verbose_name="Date de naissance")

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['first_name', 'last_name']

    objects = CustomUserManager()

    class Meta:
        db_table = 'user'
        verbose_name = 'Utilisateur'
        verbose_name_plural = 'Utilisateurs'

    def __str__(self):
        return f"{self.first_name} {self.last_name} ({self.email})"

    def add_role(self, role_code):
        from roles.models import Role, UserRole
        role = Role.objects.get(code=role_code)
        UserRole.objects.get_or_create(user=self, role=role)

    def remove_role(self, role_code):
        from roles.models import Role, UserRole
        role = Role.objects.get(code=role_code)
        UserRole.objects.filter(user=self, role=role).delete()

    def has_role(self, role_code):
        # codes des rôles actifs chargés une seule fois par instance (le menu teste ~10 fois par page)
        codes = getattr(self, '_active_role_codes', None)
        if codes is None:
            codes = set(self.user_roles.filter(is_active=True).values_list('role__code', flat=True))
            self._active_role_codes = codes
        return role_code in codes

    @property
    def roles(self):
        return [ur.role for ur in self.user_roles.filter(is_active=True)]
