from django import template
from django.template.defaultfilters import stringfilter

register = template.Library()



@register.filter
def get_note(dictionary, concat_args):
    """
    Utilisation: {{ notes_existantes|get_note:"etu.id,note_type" }}
    """
    try:
        etu_id, note_type = concat_args.split(',')
        return dictionary.get((int(etu_id), note_type), '')
    except (ValueError, AttributeError):
        return ''



@register.filter
def replace_comma(value):
    if value is None:
        return ""
    return str(value).replace(',', '.')


@register.filter(name='find_note')
def find_note(notes, evaluation_id):
    """Filter to find a note by evaluation ID"""
    for note in notes:
        if note.evaluation_id == evaluation_id:
            return note
    return None

