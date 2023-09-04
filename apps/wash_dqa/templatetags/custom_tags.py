from django import template

register = template.Library()

@register.filter
def format_cell(value):
    if value == 2:
        return "green"
    elif value == 1:
        return "red"
    else:
        return "ghostwhite"

@register.filter
def get_background_color(value):
    """
    Determine the background color based on the value.

    Args:
        value (float): The value for which to determine the background color.

    Returns:
        str: The background color as a CSS color string.
    """
    if value >= 2:
        return 'green'  # If the value is 2 or greater, use green background.
    elif 1 < value < 2:
        return 'yellow'  # If the value is between 1 and 2 (exclusive), use yellow background.
    elif 0 < value <= 1:
        return 'red'  # If the value is between 0 and 1 (inclusive), use red background.
    else:
        return 'ghostwhite'  # For all other cases, use a ghostwhite background.

@register.filter
def format_average_cell(value):
    """
    Formats the background color for a table cell based on the provided value.

    Args:
        value (float): The value to be used for formatting.

    Returns:
        str: The CSS class name for the background color.

    """
    if value == 5:
        # Blue background for a value of 5
        return "blue"
    elif 4 <= value < 5:
        # Green background for values between 4 (inclusive) and 5 (exclusive)
        return "green"
    elif 3 <= value < 4:
        # Light green background for values between 3 (inclusive) and 4 (exclusive)
        return "lightgreen"
    elif 2 <= value < 3:
        # Yellow background for values between 2 (inclusive) and 3 (exclusive)
        return "yellow"
    elif 1 <= value < 2:
        # Red background for values between 1 (inclusive) and 2 (exclusive)
        return "red"
    else:
        # Default ghostwhite background for all other values
        return "ghostwhite"

