"""
Smart scheduling service: room/slot suggestions that avoid double-booking
and prefer rooms with capacity >= section size.

Rule-based logic for ClassSchedule creation.
"""
from .models import Classroom, ClassSchedule, Section


def _times_overlap(start1, end1, start2, end2):
    """
    Check if two time slots overlap.
    Slots (s1, e1) and (s2, e2) overlap if s1 < e2 AND s2 < e1.
    """
    return start1 < end2 and start2 < end1


def is_room_available(classroom, day_of_week, start_time, end_time, exclude_schedule_id=None):
    """
    Check if a classroom is available for the given day and time slot.

    A room is available if no ClassSchedule exists for the same room, day,
    and an overlapping time range.

    Args:
        classroom: Classroom instance
        day_of_week: int (0=Monday, ..., 6=Sunday)
        start_time: time
        end_time: time
        exclude_schedule_id: optional int - when editing, exclude this schedule
            from the conflict check so we don't flag the current schedule as a conflict

    Returns:
        bool: True if room is available, False if double-booked
    """
    conflicting = (
        ClassSchedule.objects
        .filter(classroom=classroom, day_of_week=day_of_week)
        .exclude(pk=exclude_schedule_id)
    )
    for sched in conflicting:
        if _times_overlap(start_time, end_time, sched.start_time, sched.end_time):
            return False
    return True


def get_room_suggestions(section, day_of_week, start_time, end_time, exclude_schedule_id=None):
    """
    Get ranked list of available classrooms for a section and time slot.

    Rules:
    1. Avoid double-booking: exclude rooms with overlapping ClassSchedules
    2. Prefer rooms with capacity >= section size (enrolled students)
    3. Among rooms with sufficient capacity, prefer smaller rooms (better fit)
    4. Rooms that are too small are still returned but marked/ranked lower

    Args:
        section: Section instance (for student count)
        day_of_week: int (0=Monday, ..., 6=Sunday)
        start_time: time
        end_time: time
        exclude_schedule_id: optional int - when editing, exclude this schedule

    Returns:
        list of dicts: [
            {
                'classroom': Classroom,
                'capacity': int,
                'section_size': int,
                'fits': bool,      # capacity >= section_size
                'reason': str,     # e.g. "Good fit" or "May be tight"
            },
            ...
        ]
        Sorted by: fits first, then by capacity ascending (prefer right-sized rooms).
    """
    section_size = section.students.count()
    classrooms = Classroom.objects.select_related('block').all()

    suggestions = []
    for classroom in classrooms:
        if not is_room_available(classroom, day_of_week, start_time, end_time, exclude_schedule_id):
            continue

        fits = classroom.capacity >= section_size
        if fits:
            reason = "Good fit" if classroom.capacity <= section_size + 10 else "Sufficient capacity"
        else:
            reason = f"May be tight (section has {section_size} students)"

        suggestions.append({
            'classroom': classroom,
            'capacity': classroom.capacity,
            'section_size': section_size,
            'fits': fits,
            'reason': reason,
        })

    # Sort: fits first, then by capacity ascending (prefer right-sized over oversized)
    suggestions.sort(key=lambda x: (not x['fits'], x['capacity']))
    return suggestions
