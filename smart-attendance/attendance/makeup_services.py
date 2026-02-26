"""Services for make-up class remedial code generation and validation."""

import secrets
from datetime import datetime, timedelta

from django.utils import timezone

from .models import RemedialCode, MakeUpClass, Student, AttendanceRecord


# Alphanumeric characters for code generation (exclude ambiguous: 0/O, 1/I/l)
_CODE_CHARS = "23456789ABCDEFGHJKLMNPQRSTUVWXYZ"
_CODE_LENGTH = 6
_EXPIRY_BUFFER_MINUTES = 15
_MAX_GENERATION_ATTEMPTS = 10


def generate_remedial_code() -> str:
    """
    Generate a unique 6-character alphanumeric remedial code.

    Uses cryptographically secure random generation.
    Retries if collision with existing code (unlikely).
    """
    for _ in range(_MAX_GENERATION_ATTEMPTS):
        code = "".join(
            secrets.choice(_CODE_CHARS) for _ in range(_CODE_LENGTH)
        )
        if not RemedialCode.objects.filter(code=code).exists():
            return code
    raise ValueError("Could not generate unique remedial code after max attempts")


def create_remedial_code_for_makeup_class(make_up_class: MakeUpClass) -> RemedialCode:
    """
    Create a RemedialCode for a MakeUpClass.

    Code expires at end_time + 15 minutes buffer (on the scheduled date).
    Returns the created RemedialCode instance.
    """
    scheduled_date = make_up_class.scheduled_date
    end_time = make_up_class.end_time

    # Combine date and time into a timezone-aware datetime for expiry
    expires_at = datetime.combine(scheduled_date, end_time)
    expires_at = timezone.make_aware(
        expires_at,
        timezone.get_current_timezone(),
    )
    expires_at = expires_at + timedelta(minutes=_EXPIRY_BUFFER_MINUTES)

    return RemedialCode.objects.create(
        make_up_class=make_up_class,
        code=generate_remedial_code(),
        expires_at=expires_at,
    )


def get_or_create_active_remedial_code(make_up_class: "MakeUpClass") -> "RemedialCode | None":
    """
    Get an active (unused, not expired) remedial code for a make-up class.
    Creates a new one if none exists.
    Returns None only if creation fails.
    """
    active = (
        RemedialCode.objects.filter(make_up_class=make_up_class, is_used=False)
        .filter(expires_at__gt=timezone.now())
        .first()
    )
    if active:
        return active
    return create_remedial_code_for_makeup_class(make_up_class)


def validate_remedial_code(code: str):
    """
    Validate a remedial code.

    Returns:
        tuple: (remedial_code, None) if valid; (None, error_message) if invalid.
    """
    if not code or not code.strip():
        return None, "Code is required."

    code = code.strip().upper()

    try:
        remedial_code = RemedialCode.objects.select_related(
            "make_up_class", "make_up_class__section"
        ).get(code=code)
    except RemedialCode.DoesNotExist:
        return None, "Invalid code. Please check and try again."

    if remedial_code.is_used:
        return None, "This code has expired or been invalidated."

    now = timezone.now()
    if remedial_code.expires_at <= now:
        return None, "This code has expired."

    return remedial_code, None


def mark_makeup_attendance(roll_number: str, code: str):
    """
    Mark make-up attendance for a student by roll number and remedial code.

    Validates the code, finds the student in the make-up class's section,
    and creates an AttendanceRecord with record_type='make_up'.

    Returns:
        tuple: (success: bool, message: str)
    """
    remedial_code, error = validate_remedial_code(code)
    if error:
        return False, error

    if not roll_number or not roll_number.strip():
        return False, "Roll number is required."

    roll_number = roll_number.strip()

    section = remedial_code.make_up_class.section
    scheduled_date = remedial_code.make_up_class.scheduled_date

    try:
        student = Student.objects.get(
            section=section,
            roll_number__iexact=roll_number,
        )
    except Student.DoesNotExist:
        return False, f"No student with roll number '{roll_number}' in this section."

    # Check if already marked for this make-up session
    existing = AttendanceRecord.objects.filter(
        student=student,
        remedial_code=remedial_code,
    ).exists()
    if existing:
        return False, "Attendance for this make-up class is already recorded."

    AttendanceRecord.objects.create(
        student=student,
        date=scheduled_date,
        status="present",
        record_type="make_up",
        remedial_code=remedial_code,
        marked_by=None,  # Public page, no logged-in user
    )

    return True, f"Attendance marked successfully for {student.name}."
