from django import template

register = template.Library()

@register.filter
def get_item(dictionary, key):
    # Handle dictionary
    if hasattr(dictionary, 'get'):
        return dictionary.get(key)
    # Handle list/tuple with numeric index
    try:
        return dictionary[key]
    except (TypeError, KeyError, IndexError):
        return None