from django import template

register = template.Library()

@register.filter
def remove_underscores(value):
    return value.replace('_', ' ').title()

@register.filter(name='has_group')
def has_group(user, group_name):
    return user.groups.filter(name=group_name).exists()