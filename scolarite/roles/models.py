from django.db import models

from django.db import models
from django.contrib.auth.models import AbstractUser

from scolarite import settings

class Role(models.Model):
    ROLE_CHOICES = [
        ('ADMIN', 'Administrateur'),
        ('SUPER_ADMIN', 'Super Administrateur'),
        ('DOCTOR', 'Médecin'),
        ('MANAGER', 'Manager'),
        ('POINTEUR', 'Pointeur'),
        ('POINTER', 'Pointer'),
        ('PROFESSEUR', 'Professeur'),
    ]

    code = models.CharField(max_length=20, choices=ROLE_CHOICES, unique=True, verbose_name="Code du rôle")
    name = models.CharField(max_length=50, verbose_name="Nom affiché")
    description = models.TextField(blank=True, verbose_name="Description")

    class Meta:
        verbose_name = "Rôle"
        verbose_name_plural = "Rôles"

    def __str__(self):
        return self.name

class Permission(models.Model):
    code = models.CharField(max_length=100, unique=True)
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)

    def __str__(self):
        return self.name


# 3. Lier les utilisateurs aux rôles via une table intermédiaire
class UserRole(models.Model):
    user = models.ForeignKey(
        'users.User',
        on_delete=models.CASCADE,
        related_name='user_roles'
    )

    role = models.ForeignKey(
        Role,
        on_delete=models.CASCADE
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    is_active = models.BooleanField(
        default=True
    )

    class Meta:
        unique_together = ('user', 'role')
        verbose_name = "Rôle utilisateur"
        verbose_name_plural = "Rôles utilisateurs"

    def __str__(self):
        return f"{self.user} - {self.role}"
