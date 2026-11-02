from django import template
from django.utils import translation

register = template.Library()

JOURS_AR = {
    'lundi': 'الإثنين',
    'mardi': 'الثلاثاء',
    'mercredi': 'الأربعاء',
    'jeudi': 'الخميس',
    'vendredi': 'الجمعة',
    'samedi': 'السبت',
    'dimanche': 'الأحد',
    'monday': 'الإثنين',
    'tuesday': 'الثلاثاء',
    'wednesday': 'الأربعاء',
    'thursday': 'الخميس',
    'friday': 'الجمعة',
    'saturday': 'السبت',
    'sunday': 'الأحد',
}


@register.filter
def jour_i18n(value):
    """Affiche un nom de jour (stocké en français) en arabe quand la langue active est l'arabe."""
    if value and translation.get_language() and translation.get_language().startswith('ar'):
        return JOURS_AR.get(str(value).strip().lower(), value)
    return value
