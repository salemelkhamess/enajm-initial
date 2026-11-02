from django.core.exceptions import ObjectDoesNotExist
from .models import Parametres

def get_annee_courante():
    try:
        return Parametres.get_instance().annee_courante
    except ObjectDoesNotExist:
        return None

def get_trimestre_courant():
    try:
        return Parametres.get_instance().trimestre_courant
    except ObjectDoesNotExist:
        return None