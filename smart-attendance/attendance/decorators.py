"""Role-based auth decorators for faculty, student, and staff."""

from functools import wraps

from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect
from django.contrib import messages


def get_user_role(user):
    """
    Return user role: 'staff', 'faculty', 'student', or None.
    Faculty and student profiles take precedence over is_staff.
    """
    if not user or not user.is_authenticated:
        return None
    if hasattr(user, 'faculty_profile'):
        return 'faculty'
    if hasattr(user, 'student_profile'):
        return 'student'
    if user.is_staff:
        return 'staff'
    return None


def faculty_required(view_func):
    """Restrict view to faculty users."""

    @wraps(view_func)
    @login_required
    def _wrapped(request, *args, **kwargs):
        if get_user_role(request.user) == 'faculty':
            return view_func(request, *args, **kwargs)
        if get_user_role(request.user) == 'staff':
            return redirect('admin_dashboard')
        if get_user_role(request.user) == 'student':
            return redirect('student_dashboard')
        messages.error(request, 'Faculty access required.')
        return redirect('login')

    return _wrapped


def student_required(view_func):
    """Restrict view to student users."""

    @wraps(view_func)
    @login_required
    def _wrapped(request, *args, **kwargs):
        if get_user_role(request.user) == 'student':
            return view_func(request, *args, **kwargs)
        if get_user_role(request.user) == 'faculty':
            return redirect('faculty_dashboard')
        if get_user_role(request.user) == 'staff':
            return redirect('admin_dashboard')
        messages.error(request, 'Student access required.')
        return redirect('login')

    return _wrapped


def staff_required(view_func):
    """Restrict view to staff users (admin-only; excludes faculty/student)."""

    @wraps(view_func)
    @login_required
    def _wrapped(request, *args, **kwargs):
        if get_user_role(request.user) == 'staff':
            return view_func(request, *args, **kwargs)
        if get_user_role(request.user) == 'faculty':
            return redirect('faculty_dashboard')
        if get_user_role(request.user) == 'student':
            return redirect('student_dashboard')
        messages.error(request, 'Admin access required.')
        return redirect('login')

    return _wrapped


def faculty_or_staff_required(view_func):
    """Restrict view to faculty or staff users."""

    @wraps(view_func)
    @login_required
    def _wrapped(request, *args, **kwargs):
        role = get_user_role(request.user)
        if role in ('faculty', 'staff'):
            return view_func(request, *args, **kwargs)
        if role == 'student':
            return redirect('student_dashboard')
        messages.error(request, 'Faculty or admin access required.')
        return redirect('login')

    return _wrapped
