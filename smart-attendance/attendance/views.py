from datetime import date, timedelta

from django.shortcuts import render, redirect, get_object_or_404
from django.utils import timezone
from django.contrib.auth.decorators import login_required
from django.contrib import messages

from .models import Student, Section, AttendanceRecord, Faculty, Block, ClassSchedule, MakeUpClass
from notifications.models import NotificationLog
from .forms import (
    StudentCreateForm,
    StudentUpdateForm,
    StudentRegisterForm,
    FacultyCreateForm,
    MakeUpClassCreateForm,
    ClassScheduleCreateForm,
)
from .makeup_services import create_remedial_code_for_makeup_class, mark_makeup_attendance, get_or_create_active_remedial_code
from .scheduling_service import get_room_suggestions
from .decorators import get_user_role, faculty_required, student_required, staff_required, faculty_or_staff_required


def index(request):
    """Redirect root to role-appropriate dashboard if logged in, else to login."""
    if request.user.is_authenticated:
        role = get_user_role(request.user)
        if role == 'staff':
            return redirect('admin_dashboard')
        if role == 'faculty':
            return redirect('faculty_dashboard')
        if role == 'student':
            return redirect('student_dashboard')
        return redirect('login')
    return redirect('login')


def dashboard_router(request):
    """Post-login redirect: send user to their role-specific dashboard."""
    if not request.user.is_authenticated:
        return redirect('login')
    role = get_user_role(request.user)
    if role == 'staff':
        return redirect('admin_dashboard')
    if role == 'faculty':
        return redirect('faculty_dashboard')
    if role == 'student':
        return redirect('student_dashboard')
    return redirect('login')


def faculty_register(request):
    """Public self-registration for faculty."""
    if request.user.is_authenticated:
        return redirect('dashboard')
    if request.method == 'POST':
        form = FacultyCreateForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Registration successful. Please log in.')
            return redirect('login')
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        form = FacultyCreateForm()
    return render(request, 'attendance/faculty_register.html', {'form': form})


def student_register(request):
    """Public self-registration for students. Links existing student record to new User."""
    if request.user.is_authenticated:
        return redirect('dashboard')
    if request.method == 'POST':
        form = StudentRegisterForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Account created. Please log in.')
            return redirect('login')
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        form = StudentRegisterForm()
    return render(request, 'attendance/student_register.html', {'form': form})


@login_required
def faculty_dashboard(request):
    """Faculty dashboard: sections they teach, with links to mark attendance."""
    faculty = getattr(request.user, 'faculty_profile', None)
    if not faculty:
        if request.user.is_staff:
            return redirect('admin_dashboard')
        if getattr(request.user, 'student_profile', None):
            return redirect('student_dashboard')
        messages.error(request, 'Faculty access required.')
        return redirect('login')

    sections = (
        Section.objects
        .filter(course__faculty_assignments__faculty=faculty)
        .select_related('course')
        .prefetch_related('students')
        .distinct()
    )
    return render(request, 'attendance/faculty_dashboard.html', {'sections': sections})


@student_required
def student_dashboard(request):
    """Student dashboard: my section, attendance summary, schedule."""
    student = request.user.student_profile
    section = student.section
    # Attendance stats (last 30 days)
    cutoff = timezone.now().date() - timedelta(days=30)
    records = AttendanceRecord.objects.filter(
        student=student,
        date__gte=cutoff,
        record_type='regular',
    ).order_by('-date')[:20]
    total_days = AttendanceRecord.objects.filter(
        student=student,
        date__gte=cutoff,
        record_type='regular',
    ).values('date').distinct().count()
    present_count = AttendanceRecord.objects.filter(
        student=student,
        date__gte=cutoff,
        record_type='regular',
        status='present',
    ).count()
    attendance_pct = round((present_count / total_days * 100), 1) if total_days else 0
    # Class schedule for this section
    schedules = ClassSchedule.objects.filter(
        section=section
    ).select_related('classroom', 'classroom__block').order_by('day_of_week', 'start_time')
    return render(request, 'attendance/student_dashboard.html', {
        'student': student,
        'section': section,
        'records': records,
        'attendance_pct': attendance_pct,
        'total_days': total_days,
        'schedules': schedules,
    })


@staff_required
def admin_dashboard(request):
    """Admin dashboard: overview with links to manage faculty, students, sections."""
    from django.db.models import Count
    sections = Section.objects.select_related('course').annotate(
        student_count=Count('students')
    ).all()
    faculty_count = Faculty.objects.count()
    student_count = Student.objects.count()
    return render(request, 'attendance/admin_dashboard.html', {
        'sections': sections,
        'faculty_count': faculty_count,
        'student_count': student_count,
    })


@faculty_or_staff_required
def notification_logs(request):
    """List all simulated notification logs."""
    logs = NotificationLog.objects.all()[:100]  # Limit to recent 100
    return render(request, 'attendance/notification_logs.html', {'notification_logs': logs})


@staff_required
def faculty_list(request):
    """List all faculty. Restricted to staff users."""
    faculty = Faculty.objects.select_related('user').all().order_by('user__username')
    return render(request, 'attendance/faculty_list.html', {'faculty_list': faculty})


@staff_required
def faculty_create(request):
    """Create a new faculty member. Restricted to staff users."""
    if request.method == 'POST':
        form = FacultyCreateForm(request.POST)
        if form.is_valid():
            user = form.save()
            messages.success(request, f'Faculty "{user.username}" created successfully.')
            return redirect('faculty_list')
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        form = FacultyCreateForm()
    return render(request, 'attendance/faculty_form.html', {'form': form})


@faculty_or_staff_required
def student_list(request):
    """List all students; optionally filter by section."""
    section_id = request.GET.get('section')
    students = Student.objects.select_related('section', 'section__course').all()
    if section_id:
        students = students.filter(section_id=section_id)
    sections = Section.objects.select_related('course').all()
    return render(request, 'attendance/student_list.html', {
        'students': students,
        'sections': sections,
        'selected_section_id': section_id,
    })


@faculty_or_staff_required
def student_create(request):
    """Create a new student. Faculty who creates is stored as created_by."""
    if request.method == 'POST':
        form = StudentCreateForm(request.POST)
        if form.is_valid():
            student = form.save(commit=False)
            student.created_by = request.user
            student.save()
            messages.success(request, f'Student "{student.name}" created successfully.')
            return redirect('student_list')
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        form = StudentCreateForm()
    return render(request, 'attendance/student_form.html', {'form': form, 'is_edit': False})


@faculty_or_staff_required
def student_edit(request, pk):
    """Edit an existing student's contact details."""
    student = get_object_or_404(Student, pk=pk)
    if request.method == 'POST':
        form = StudentUpdateForm(request.POST, instance=student)
        if form.is_valid():
            form.save()
            messages.success(request, f'Student "{student.name}" updated successfully.')
            return redirect('student_list')
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        form = StudentUpdateForm(instance=student)
    return render(
        request,
        'attendance/student_form.html',
        {'form': form, 'student': student, 'is_edit': True},
    )


@faculty_required
def mark_attendance(request, section_id):
    """
    Mark attendance for a section.
    GET: Form with student list and toggles; Mark All Present / Save.
    POST: Save records, detect absentees, simulate notifications, redirect.
    """
    section = get_object_or_404(Section.objects.prefetch_related('students'), pk=section_id)
    students = list(section.students.order_by('roll_number'))

    if request.method == 'POST':
        att_date_str = request.POST.get('date')
        try:
            att_date = date.fromisoformat(att_date_str) if att_date_str else date.today()
        except ValueError:
            att_date = date.today()
        present_ids = set(int(pk) for pk in request.POST.getlist('present') if pk.isdigit())

        # 1. Create AttendanceRecord (present) for each student marked present
        for student in students:
            if student.pk in present_ids:
                AttendanceRecord.objects.update_or_create(
                    student=student,
                    date=att_date,
                    defaults={'status': 'present', 'marked_by': request.user},
                )

        # 2. Absentee detection: compare section students vs. students with AttendanceRecord
        #    for (section, date). Students without a record → absent.
        student_ids_with_record = set(
            AttendanceRecord.objects.filter(
                student__section=section,
                date=att_date,
            ).values_list('student_id', flat=True)
        )
        absentees = [s for s in students if s.pk not in student_ids_with_record]

        # 3. Create AttendanceRecord (absent) for each absentee
        for student in absentees:
            AttendanceRecord.objects.update_or_create(
                student=student,
                date=att_date,
                defaults={'status': 'absent', 'marked_by': request.user},
            )

        # 4. Simulate notifications for absentees (student + parent)
        if absentees:
            from notifications.services import simulate_notify_student, simulate_notify_parent
            for student in absentees:
                simulate_notify_student(student.email, student.name, att_date)
                if student.parent_email:
                    simulate_notify_parent(student.parent_email, student.name, att_date)

        present_count = len(present_ids)
        absent_count = len(absentees)
        messages.success(
            request,
            f'Attendance saved for {section}. {present_count} present, {absent_count} absent. '
            'Notifications sent to absentees and parents.',
        )
        return redirect('faculty_dashboard')

    # GET: show form with student list
    today = date.today()
    return render(
        request,
        'attendance/mark_attendance.html',
        {
            'section': section,
            'students': students,
            'date': today,
        },
    )


def _parse_time(s):
    """Parse time string HH:MM or H:MM to time object. Returns None if invalid."""
    from datetime import time
    if not s or not s.strip():
        return None
    try:
        parts = s.strip().split(':')
        if len(parts) >= 2:
            h, m = int(parts[0]), int(parts[1])
            if 0 <= h <= 23 and 0 <= m <= 59:
                return time(h, m)
    except (ValueError, IndexError):
        pass
    return None


@faculty_or_staff_required
def campus_resources(request):
    """List blocks and classrooms (campus resources). Faculty-only view."""
    blocks = Block.objects.prefetch_related('classrooms').all()
    schedules = ClassSchedule.objects.select_related(
        'section', 'section__course', 'classroom', 'classroom__block'
    ).all().order_by('day_of_week', 'start_time')
    return render(request, 'attendance/campus_resources.html', {
        'blocks': blocks,
        'schedules': schedules,
    })


@faculty_or_staff_required
def schedule_create(request):
    """Create a class schedule with smart room suggestions (avoids double-booking)."""
    suggestions = []

    if request.method == 'POST':
        form = ClassScheduleCreateForm(request.POST)
        if form.is_valid():
            schedule = form.save()
            messages.success(
                request,
                f'Schedule created: {schedule.section} in {schedule.classroom} '
                f'on {schedule.get_day_of_week_display()} {schedule.start_time.strftime("%H:%M")}-{schedule.end_time.strftime("%H:%M")}.',
            )
            return redirect('campus_resources')
        else:
            # Compute suggestions from form data for display
            section_id = request.POST.get('section')
            day = request.POST.get('day_of_week')
            start_s = request.POST.get('start_time')
            end_s = request.POST.get('end_time')
            if section_id and day is not None and start_s and end_s:
                try:
                    section = Section.objects.prefetch_related('students').get(pk=section_id)
                    start_time = _parse_time(start_s)
                    end_time = _parse_time(end_s)
                    if start_time and end_time and start_time < end_time:
                        suggestions = get_room_suggestions(section, int(day), start_time, end_time)
                except (Section.DoesNotExist, ValueError, TypeError):
                    pass
    else:
        form = ClassScheduleCreateForm()
        # Optional: GET params for prefilled suggestions
        section_id = request.GET.get('section')
        day = request.GET.get('day_of_week')
        start_s = request.GET.get('start_time')
        end_s = request.GET.get('end_time')
        if section_id and day is not None and start_s and end_s:
            try:
                section = Section.objects.prefetch_related('students').get(pk=section_id)
                start_time = _parse_time(start_s)
                end_time = _parse_time(end_s)
                if start_time and end_time and start_time < end_time:
                    suggestions = get_room_suggestions(section, int(day), start_time, end_time)
            except (Section.DoesNotExist, ValueError, TypeError):
                pass

    return render(request, 'attendance/schedule_form.html', {
        'form': form,
        'suggestions': suggestions,
        'is_edit': False,
    })


@faculty_or_staff_required
def schedule_edit(request, pk):
    """Edit a class schedule. Uses scheduling service to avoid double-booking."""
    schedule = get_object_or_404(
        ClassSchedule.objects.select_related('section', 'classroom'),
        pk=pk,
    )
    suggestions = []

    if request.method == 'POST':
        form = ClassScheduleCreateForm(request.POST, instance=schedule)
        if form.is_valid():
            form.save()
            messages.success(request, 'Schedule updated successfully.')
            return redirect('campus_resources')
        else:
            section_id = request.POST.get('section')
            day = request.POST.get('day_of_week')
            start_s = request.POST.get('start_time')
            end_s = request.POST.get('end_time')
            if section_id and day is not None and start_s and end_s:
                try:
                    section = Section.objects.prefetch_related('students').get(pk=section_id)
                    start_time = _parse_time(start_s)
                    end_time = _parse_time(end_s)
                    if start_time and end_time and start_time < end_time:
                        suggestions = get_room_suggestions(
                            section, int(day), start_time, end_time,
                            exclude_schedule_id=schedule.pk,
                        )
                except (Section.DoesNotExist, ValueError, TypeError):
                    pass
    else:
        form = ClassScheduleCreateForm(instance=schedule)
        suggestions = get_room_suggestions(
            schedule.section,
            schedule.day_of_week,
            schedule.start_time,
            schedule.end_time,
            exclude_schedule_id=schedule.pk,
        )

    return render(request, 'attendance/schedule_form.html', {
        'form': form,
        'schedule': schedule,
        'suggestions': suggestions,
        'is_edit': True,
    })


@faculty_or_staff_required
def schedule_delete(request, pk):
    """Delete a class schedule."""
    schedule = get_object_or_404(ClassSchedule, pk=pk)
    if request.method == 'POST':
        section_str = str(schedule.section)
        schedule.delete()
        messages.success(request, f'Schedule for {section_str} removed.')
        return redirect('campus_resources')
    return render(request, 'attendance/schedule_confirm_delete.html', {'schedule': schedule})


@faculty_or_staff_required
def analytics_dashboard(request):
    """Analytics dashboard: capacity utilization, workload distribution, and rush prediction."""
    from .analytics import get_capacity_utilization, get_rush_prediction, get_workload_distribution
    capacity_data = get_capacity_utilization()
    workload_data = get_workload_distribution()
    rush_data = get_rush_prediction()
    return render(request, 'attendance/analytics.html', {
        'capacity_data': capacity_data,
        'workload_data': workload_data,
        'rush_data': rush_data,
    })


@faculty_required
def makeup_list(request):
    """List make-up classes scheduled by the current faculty member."""
    make_up_classes = (
        MakeUpClass.objects
        .filter(scheduled_by=request.user)
        .select_related('section', 'section__course', 'classroom', 'classroom__block')
        .prefetch_related('remedial_codes')
        .order_by('-scheduled_date', '-start_time')
    )
    return render(request, 'attendance/makeup_list.html', {
        'make_up_classes': make_up_classes,
        'now': timezone.now(),
    })


@faculty_required
def makeup_create(request):
    """Schedule a make-up class. Creates MakeUpClass and auto-generates RemedialCode."""
    if request.method == 'POST':
        form = MakeUpClassCreateForm(request.POST)
        if form.is_valid():
            make_up_class = form.save(commit=False)
            make_up_class.scheduled_by = request.user
            make_up_class.save()
            create_remedial_code_for_makeup_class(make_up_class)
            messages.success(
                request,
                f'Make-up class scheduled for {make_up_class.section} on {make_up_class.scheduled_date}. '
                'A remedial code has been generated for student attendance.',
            )
            return redirect('makeup_list')
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        form = MakeUpClassCreateForm()
    return render(request, 'attendance/makeup_create.html', {'form': form})


@faculty_required
def makeup_code(request, pk):
    """
    View or regenerate remedial code for a make-up class.
    Faculty-only; must be the scheduled_by user.
    """
    make_up_class = get_object_or_404(
        MakeUpClass.objects.select_related('section', 'section__course', 'classroom').prefetch_related('remedial_codes'),
        pk=pk,
    )
    if make_up_class.scheduled_by != request.user:
        messages.error(request, 'You do not have permission to view this make-up class.')
        return redirect('makeup_list')

    if request.method == 'POST':
        from .makeup_services import create_remedial_code_for_makeup_class
        make_up_class.remedial_codes.filter(is_used=False).update(is_used=True)
        new_code = create_remedial_code_for_makeup_class(make_up_class)
        messages.success(
            request,
            f'New remedial code generated: {new_code.code}. It expires at {new_code.expires_at.strftime("%Y-%m-%d %H:%M")}.',
        )
        return redirect('makeup_code', pk=pk)

    active_code = make_up_class.remedial_codes.filter(is_used=False).first()
    return render(request, 'attendance/makeup_code.html', {
        'make_up_class': make_up_class,
        'active_code': active_code,
        'now': timezone.now(),
    })


@faculty_required
def makeup_mark_attendance(request, pk):
    """
    Mark make-up attendance for a section - student list with present/absent toggles,
    same UX as regular attendance.
    """
    make_up_class = get_object_or_404(
        MakeUpClass.objects.select_related('section', 'section__course', 'classroom')
        .prefetch_related('remedial_codes'),
        pk=pk,
    )
    if make_up_class.scheduled_by != request.user:
        messages.error(request, 'You do not have permission to mark attendance for this make-up class.')
        return redirect('makeup_list')

    section = make_up_class.section
    students = list(section.students.order_by('roll_number'))

    if request.method == 'POST':
        remedial_code = get_or_create_active_remedial_code(make_up_class)
        if not remedial_code:
            messages.error(request, 'Could not obtain a valid remedial code. Please regenerate from the code page.')
            return redirect('makeup_code', pk=pk)

        present_ids = set(int(pk) for pk in request.POST.getlist('present') if pk.isdigit())
        att_date = make_up_class.scheduled_date

        for student in students:
            status = 'present' if student.pk in present_ids else 'absent'
            AttendanceRecord.objects.update_or_create(
                student=student,
                remedial_code=remedial_code,
                defaults={
                    'date': att_date,
                    'status': status,
                    'record_type': 'make_up',
                    'marked_by': request.user,
                },
            )

        present_count = len(present_ids)
        absent_count = len(students) - present_count
        messages.success(
            request,
            f'Make-up attendance saved for {section} on {att_date}. '
            f'{present_count} present, {absent_count} absent.',
        )
        return redirect('makeup_list')

    # GET: show form with student list, pre-check who's already marked present
    remedial_code = get_or_create_active_remedial_code(make_up_class)
    already_present_ids = set()
    if remedial_code:
        already_present_ids = set(
            AttendanceRecord.objects.filter(
                remedial_code=remedial_code,
                status='present',
            ).values_list('student_id', flat=True)
        )

    return render(
        request,
        'attendance/mark_makeup_attendance.html',
        {
            'make_up_class': make_up_class,
            'section': section,
            'students': students,
            'already_present_ids': already_present_ids,
        },
    )


def makeup_mark(request):
    """
    Public page (no login) for students to mark make-up attendance.
    Students enter roll_number + remedial_code.
    """
    if request.method == 'POST':
        roll_number = request.POST.get('roll_number', '').strip()
        code = request.POST.get('code', '').strip()

        success, message = mark_makeup_attendance(roll_number, code)
        if success:
            messages.success(request, message)
            return redirect('makeup_mark')
        else:
            messages.error(request, message)

    return render(request, 'attendance/makeup_mark.html')
