"""Simulated notification services for attendance alerts."""

from .models import NotificationLog


def _format_date(date) -> str:
    """Format date for display in notification messages."""
    if hasattr(date, "strftime"):
        return date.strftime("%Y-%m-%d")
    return str(date)


def simulate_notify_student(email: str, student_name: str, date) -> NotificationLog:
    """Simulate sending an absentee notification to a student."""
    date_str = _format_date(date)
    message = (
        f"Dear {student_name},\n\n"
        f"You were marked absent on {date_str}. "
        "Please contact your faculty if this is an error."
    )
    return NotificationLog.objects.create(
        recipient_type=NotificationLog.RecipientType.STUDENT,
        recipient_email=email or "no-email@example.com",
        message=message,
        simulated=True,
    )


def simulate_notify_parent(email: str, student_name: str, date) -> NotificationLog:
    """Simulate sending an absentee notification to a parent/guardian."""
    date_str = _format_date(date)
    message = (
        f"Dear Parent/Guardian,\n\n"
        f"Your child {student_name} was marked absent on {date_str}. "
        "Please ensure they attend classes regularly."
    )
    return NotificationLog.objects.create(
        recipient_type=NotificationLog.RecipientType.PARENT,
        recipient_email=email or "no-email@example.com",
        message=message,
        simulated=True,
    )


def send_faculty_alert(email: str, subject: str, message: str) -> NotificationLog:
    """Send an alert notification to faculty (logged via NotificationLog)."""
    full_message = f"Subject: {subject}\n\n{message}"
    return NotificationLog.objects.create(
        recipient_type=NotificationLog.RecipientType.FACULTY,
        recipient_email=email or "no-email@example.com",
        message=full_message,
        simulated=True,
    )
