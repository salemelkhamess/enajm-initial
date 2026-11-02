from django.db import models
from django.utils import timezone



class Professeur(models.Model):
    class Meta:
        db_table = 'professeurs'

    nom = models.CharField(max_length=100)
    prenom = models.CharField(max_length=100)
    email = models.EmailField()
    telephone = models.CharField(max_length=20)
    specialite = models.CharField(max_length=100)
    user = models.OneToOneField(
        'users.User', null=True, blank=True, on_delete=models.SET_NULL,
        related_name='professeur', verbose_name="Compte utilisateur",
        help_text="Compte avec lequel ce professeur se connecte (rôle Professeur)."
    )

    def __str__(self):
        return  f"{self.nom} {self.prenom}"


class AttestationCounter(models.Model):
    year = models.IntegerField(unique=True)
    last_number = models.IntegerField(default=0)

    @classmethod
    def get_next_number(cls, year):
        counter, created = cls.objects.get_or_create(
            year=year,
            defaults={'last_number': 0}
        )
        counter.last_number += 1
        counter.save()
        return counter.last_number


class AttestationEnseignement(models.Model):
    professeur = models.ForeignKey(Professeur, on_delete=models.CASCADE)
    date_creation = models.DateField(auto_now_add=True)
    numero = models.CharField(max_length=20, unique=True)
    annee = models.IntegerField()

    class Meta:
        unique_together = ('professeur', 'annee')

    @classmethod
    def get_or_create_for_professor(cls, professeur):
        current_year = timezone.now().year

        # Vérifier si une attestation existe déjà
        existing = cls.objects.filter(professeur=professeur, annee=current_year).first()
        if existing:
            return existing

        # Si elle n'existe pas, créer une nouvelle attestation avec un nouveau numéro
        new_number = AttestationCounter.get_next_number(current_year)
        return cls.objects.create(
            professeur=professeur,
            numero=f"{new_number}/{current_year}",
            annee=current_year
        )