"""Views for notifications app."""

import json
from datetime import date

from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt

from attendance.models import Student
from .services import simulate_notify_student, simulate_notify_parent


def _parse_json_body(request):
    """Parse JSON from request body. Return (data, error_response) tuple."""
    if not request.body:
        return None, JsonResponse({'success': False, 'error': 'Request body is required'}, status=400)
    try:
        data = json.loads(request.body.decode('utf-8'))
        return data, None
    except json.JSONDecodeError:
        return None, JsonResponse({'success': False, 'error': 'Invalid JSON'}, status=400)


def _format_date(d):
    """Parse date string or use today."""
    if d is None:
        return date.today()
    if hasattr(d, 'year'):
        return d
    try:
        return date.fromisoformat(str(d))
    except (ValueError, TypeError):
        return date.today()


@require_http_methods(['POST'])
@csrf_exempt
def simulate_notification(request):
    """
    Simulate sending attendance notifications.

    POST JSON body. Two modes:

    1. By student_id (sends to student + parent):
       {"student_id": 1, "date": "2025-02-22"}

    2. Single notification:
       {"recipient_email": "x@example.com", "recipient_type": "student"|"parent",
        "student_name": "John Doe", "date": "2025-02-22"}
    """
    data, err = _parse_json_body(request)
    if err:
        return err

    # Mode 1: Simulate for a student by ID
    student_id = data.get('student_id')
    if student_id is not None:
        try:
            student = Student.objects.get(pk=student_id)
        except (Student.DoesNotExist, ValueError):
            return JsonResponse(
                {'success': False, 'error': 'Student not found'},
                status=404
            )
        att_date = _format_date(data.get('date'))
        logs = []
        log1 = simulate_notify_student(student.email or 'no-email@example.com', student.name, att_date)
        logs.append({'id': log1.id, 'recipient_type': 'student', 'recipient_email': log1.recipient_email})
        if student.parent_email:
            log2 = simulate_notify_parent(student.parent_email, student.name, att_date)
            logs.append({'id': log2.id, 'recipient_type': 'parent', 'recipient_email': log2.recipient_email})
        return JsonResponse({
            'success': True,
            'notifications_sent': len(logs),
            'student_name': student.name,
            'date': att_date.isoformat(),
            'logs': logs,
        })

    # Mode 2: Single notification
    recipient_email = data.get('recipient_email')
    recipient_type = data.get('recipient_type', 'student')
    student_name = data.get('student_name', 'Student')

    if not recipient_email:
        return JsonResponse(
            {'success': False, 'error': 'recipient_email is required for single notification'},
            status=400
        )
    if recipient_type not in ('student', 'parent'):
        return JsonResponse(
            {'success': False, 'error': 'recipient_type must be "student" or "parent"'},
            status=400
        )

    att_date = _format_date(data.get('date'))
    if recipient_type == 'student':
        log = simulate_notify_student(recipient_email, student_name, att_date)
    else:
        log = simulate_notify_parent(recipient_email, student_name, att_date)

    return JsonResponse({
        'success': True,
        'notifications_sent': 1,
        'log': {'id': log.id, 'recipient_type': recipient_type, 'recipient_email': log.recipient_email},
        'date': att_date.isoformat(),
    })
