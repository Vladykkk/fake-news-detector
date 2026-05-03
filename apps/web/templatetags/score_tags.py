"""Custom template tags/filters for score display."""
from django import template

register = template.Library()


@register.filter
def as_percent(value):
    """Convert 0.0-1.0 score to percentage string (e.g., 0.667 → 66.7)."""
    try:
        return f"{float(value) * 100:.1f}"
    except (ValueError, TypeError):
        return "0.0"
