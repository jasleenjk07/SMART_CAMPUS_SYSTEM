"""Template context processors for role-based nav."""

from .decorators import get_user_role


def user_role(request):
    """Add user_role to template context for role-based navigation."""
    return {
        'user_role': get_user_role(request.user) if request.user.is_authenticated else None,
    }
