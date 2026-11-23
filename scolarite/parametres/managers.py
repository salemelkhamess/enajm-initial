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

    lookup_defaut = 'annee'

    def __new__(cls, lookup=None):
        # Django recrée le manager pour les relations inverses (etudiant.documents, evaluation.note_set…) sans
        # repasser `lookup` : on le mémorise dans une sous-classe pour que ces relations gardent le bon chemin.
        if lookup and cls is AnneeFilteredManager:
            cls = type(f'AnneeFilteredManager_{lookup}', (AnneeFilteredManager,), {'lookup_defaut': lookup})
        return super().__new__(cls)

    def __init__(self, lookup=None):
        super().__init__()
        self.lookup = lookup or self.lookup_defaut

    def get_queryset(self):
        qs = super().get_queryset()
        try:
            annee_id = annee_effective_id()
        except Exception:  # table absente (migrate initial, etc.)
            return qs
        if annee_id:
            qs = qs.filter(**{self.lookup: annee_id})
        return qs
