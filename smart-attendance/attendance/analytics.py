"""
Analytics services: capacity utilization, workload distribution, and rush prediction.
"""
from django.db.models import Count
from django.db.models.functions import ExtractHour

from .models import AttendanceRecord, Block, Faculty, FacultyCourseAssignment, Section


def get_capacity_utilization():
    """
    Compute per-classroom and per-block capacity utilization.
    Utilization = (enrolled_students / capacity) * 100 across scheduled slots.
    Returns list of dicts: [{block, classrooms: [{classroom, capacity, enrolled, utilization}]}]
    """
    blocks = Block.objects.prefetch_related('classrooms', 'classrooms__class_schedules').all()
    result = []

    for block in blocks:
        block_classrooms = []
        block_total_util = 0
        block_count = 0

        for classroom in block.classrooms.all():
            schedules = classroom.class_schedules.select_related('section').prefetch_related('section__students')
            if not schedules.exists():
                block_classrooms.append({
                    'classroom': classroom,
                    'capacity': classroom.capacity,
                    'enrolled': 0,
                    'utilization': 0,
                    'schedules_count': 0,
                })
                continue

            total_enrolled = 0
            for sched in schedules:
                enrolled = sched.section.students.count()
                total_enrolled += enrolled

            avg_enrolled = total_enrolled / schedules.count() if schedules else 0
            utilization = (avg_enrolled / classroom.capacity * 100) if classroom.capacity else 0
            block_classrooms.append({
                'classroom': classroom,
                'capacity': classroom.capacity,
                'enrolled': int(avg_enrolled),
                'utilization': round(utilization, 1),
                'schedules_count': schedules.count(),
            })
            block_total_util += utilization
            block_count += 1

        block_avg_util = round(block_total_util / block_count, 1) if block_count else 0
        result.append({
            'block': block,
            'classrooms': block_classrooms,
            'block_avg_utilization': block_avg_util,
        })

    return result


def get_workload_distribution():
    """
    Per faculty: count of courses/sections assigned, total credits taught.
    Returns list of dicts: [{faculty, courses_count, sections_count, total_credits}]
    """
    faculty = Faculty.objects.select_related('user').prefetch_related(
        'course_assignments',
        'course_assignments__course',
        'course_assignments__course__sections',
    ).all()

    result = []
    for f in faculty:
        assignments = f.course_assignments.select_related('course').all()
        courses_count = assignments.count()
        total_credits = sum((a.course.credits or 0) for a in assignments)
        sections_count = Section.objects.filter(course__faculty_assignments__faculty=f).distinct().count()

        result.append({
            'faculty': f,
            'courses_count': courses_count,
            'sections_count': sections_count,
            'total_credits': total_credits,
        })

    return result


def get_rush_prediction():
    """
    Aggregate attendance records by hour to identify peak (rush) times.
    Groups by hour of marked_at; higher counts indicate busier periods.
    Returns list of dicts: [{hour, hour_label, count}], sorted by count desc.
    """
    qs = (
        AttendanceRecord.objects
        .annotate(hour=ExtractHour('marked_at'))
        .values('hour')
        .annotate(count=Count('id'))
    )
    hour_counts = {r['hour']: r['count'] for r in qs}

    result = []
    for h in range(24):
        count = hour_counts.get(h, 0)
        if h == 0:
            label = "12-1 AM"
        elif h < 12:
            label = f"{h}-{h + 1} AM"
        elif h == 12:
            label = "12-1 PM"
        else:
            label = f"{h - 12}-{h - 11} PM"
        result.append({'hour': h, 'hour_label': label, 'count': count})

    result.sort(key=lambda x: (-x['count'], x['hour']))
    return result
