from datetime import timedelta

from django import template
from django.utils import timezone

register = template.Library()

@register.filter
def remove_underscores(value):
    return value.replace('_', ' ').title()

@register.filter(name='has_group')
def has_group(user, group_name):
    return user.groups.filter(name=group_name).exists()

@register.filter(name='has_group_permission')
def has_group_permission(user, group_names):
    return any(group.name in group_names for group in user.groups.all())

@register.filter(name='days_since')
def days_since(value):
    delta = timezone.now() - value
    return delta.days

@register.filter(name='within_current_month')
def within_current_month(value):
    now = timezone.now()
    return value.year == now.year and value.month == now.month

@register.filter
def format_file_size(value):
    try:
        size = int(value)
    except (TypeError, ValueError):
        return value

    if size < 1024:
        return f"{size} B"
    elif 1024 <= size < 1024 * 1024:
        return f"{size / 1024:.2f} KB"
    else:
        return f"{size / (1024 * 1024):.2f} MB"