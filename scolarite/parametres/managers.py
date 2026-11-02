# parametres/managers.py
from django.db import models

from .middleware import annee_effective_id


class AnneeFilteredManager(models.Manager):
    """
    Manager par défaut qui ne retourne que les données de l'année affichée
    (année consultée dans la session, sinon année active des paramètres).

    `lookup` est le chemin vers l'année, ex. 'annee' ou 'trimestre__annee'.
    Les accès par clé étrangère (obj.etudiant) ne sont pas filtrés.
    """

    def __init__(self, lookup='annee'):
        super().__init__()
        self.lookup = lookup

    def get_queryset(self):
        qs = super().get_queryset()
        try:
            annee_id = annee_effective_id()
        except Exception:  # table absente (migrate initial, etc.)
            return qs
        if annee_id:
            qs = qs.filter(**{self.lookup: annee_id})
        return qs
