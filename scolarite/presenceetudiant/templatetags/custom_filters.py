
from django import template
from datetime import timedelta, datetime ,date
from django.utils import timezone

register = template.Library()

@register.filter
def get_item(dictionary, key):
    return dictionary.get(key, '')

@register.filter(name='time_since')
def time_since(value, hours):
    """Check if the date is older than X hours."""
    if not value:
        return False

    now = timezone.now()

    # If value is a date (not datetime), convert it to datetime at midnight
    if isinstance(value, date) and not isinstance(value, datetime):
        value = datetime.combine(value, datetime.min.time())
        value = timezone.make_aware(value)  # Make it timezone-aware

    delta = now - value
    return delta > timedelta(hours=hours)

@register.filter
def multiply(value, arg):
    """Multiplie la valeur par l'argument"""
    return value * arg

def get_jour_display_ar(self):
    jours_ar = {
        'Lundi': 'الإثنين',
        'Mardi': 'الثلاثاء',
        'Mercredi': 'الأربعاء',
        'Jeudi': 'الخميس',
        'Vendredi': 'الجمعة',
        'Samedi': 'السبت'
    }
    return jours_ar.get(self.jour, self.jour)




@register.filter
def sum_attr(queryset, attr):
    return sum(getattr(item, attr, 0) for item in queryset)
