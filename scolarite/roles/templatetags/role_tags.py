from django import template

register = template.Library()

@register.filter
def has_any_role(user, roles):
    if not user.is_authenticated:
        return False
    role_codes = [r.strip() for r in roles.split(',')]
    return any(user.has_role(role_code) for role_code in role_codes)

@register.filter
def as_crispy_field(field):
    return field.as_widget(attrs=field.field.widget.attrs)