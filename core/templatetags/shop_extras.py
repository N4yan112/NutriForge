from decimal import Decimal
from django import template

register = template.Library()


@register.filter
def inr(value):
    """12345.6 -> ₹12,346  (Indian digit grouping)."""
    try:
        number = int(round(Decimal(value)))
    except (TypeError, ValueError, ArithmeticError):
        return value
    digits = str(abs(number))
    if len(digits) > 3:
        head, tail = digits[:-3], digits[-3:]
        parts = []
        while len(head) > 2:
            parts.insert(0, head[-2:])
            head = head[:-2]
        if head:
            parts.insert(0, head)
        digits = ','.join(parts + [tail])
    return f"{'-' if number < 0 else ''}₹{digits}"


@register.filter
def mul(value, arg):
    return value * arg
