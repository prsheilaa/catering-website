from django import template

register = template.Library()

@register.filter
def rupiah(value):
    try:
        return "Rp {:,.0f}".format(value).replace(",", ".")
    except (ValueError, TypeError):
        return value