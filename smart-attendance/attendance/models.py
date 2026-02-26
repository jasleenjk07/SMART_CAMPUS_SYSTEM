from django.db import models
from django.db.models import Q
from django.conf import settings


class Block(models.Model):
    """Campus building block (e.g., 'Block A', 'Science Block')."""
    name = models.CharField(max_length=100)
    code = models.CharField(max_length=20, unique=True)

    class Meta:
        ordering = ['code']

    def __str__(self):
        return f"{self.code} - {self.name}"


class Classroom(models.Model):
    """Room within a block."""
    name = models.CharField(max_length=100)
    block = models.ForeignKey(
        Block,
        on_delete=models.CASCADE,
        related_name='classrooms',
    )
    room_number = models.CharField(max_length=20)
    capacity = models.PositiveIntegerField(default=30)

    class Meta:
        ordering = ['block__code', 'room_number']
        unique_together = ['block', 'room_number']

    def __str__(self):
        return f"{self.block.code} - {self.room_number} ({self.name})"


class Faculty(models.Model):
    """Faculty profile linked to auth User. Use User for login (username/password)."""
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='faculty_profile',
    )
    department = models.CharField(max_length=100, blank=True)
    phone = models.CharField(max_length=20, blank=True)

    def __str__(self):
        return self.user.get_full_name() or self.user.username


class Course(models.Model):
    """Course offered by the institution."""
    name = models.CharField(max_length=200)
    code = models.CharField(max_length=50, unique=True)
    credits = models.PositiveIntegerField(null=True, blank=True, help_text="Credit hours for workload calculation")

    class Meta:
        ordering = ['code']

    def __str__(self):
        return f"{self.code} - {self.name}"


class FacultyCourseAssignment(models.Model):
    """Junction model for faculty-course assignment (who teaches what)."""
    faculty = models.ForeignKey(
        Faculty,
        on_delete=models.CASCADE,
        related_name='course_assignments',
    )
    course = models.ForeignKey(
        Course,
        on_delete=models.CASCADE,
        related_name='faculty_assignments',
    )

    class Meta:
        ordering = ['faculty', 'course']
        unique_together = ['faculty', 'course']

    def __str__(self):
        return f"{self.faculty} → {self.course}"


class Section(models.Model):
    """Section/class within a course."""
    name = models.CharField(max_length=100)
    course = models.ForeignKey(
        Course,
        on_delete=models.CASCADE,
        related_name='sections',
    )

    class Meta:
        ordering = ['course__code', 'name']
        unique_together = ['course', 'name']

    def __str__(self):
        return f"{self.course.code} - {self.name}"


class ClassSchedule(models.Model):
    """When and where sections meet."""
    DAY_CHOICES = [
        (0, 'Monday'),
        (1, 'Tuesday'),
        (2, 'Wednesday'),
        (3, 'Thursday'),
        (4, 'Friday'),
        (5, 'Saturday'),
        (6, 'Sunday'),
    ]
    section = models.ForeignKey(
        Section,
        on_delete=models.CASCADE,
        related_name='class_schedules',
    )
    classroom = models.ForeignKey(
        Classroom,
        on_delete=models.CASCADE,
        related_name='class_schedules',
    )
    day_of_week = models.PositiveSmallIntegerField(choices=DAY_CHOICES)
    start_time = models.TimeField()
    end_time = models.TimeField()

    class Meta:
        ordering = ['day_of_week', 'start_time']
        unique_together = ['classroom', 'day_of_week', 'start_time']

    def __str__(self):
        return f"{self.section} - {self.classroom} ({self.get_day_of_week_display()})"


class Student(models.Model):
    """Student with contact and parent details. Optional User for login."""
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='student_profile',
    )
    name = models.CharField(max_length=200)
    roll_number = models.CharField(max_length=50)
    email = models.EmailField(blank=True)
    phone = models.CharField(max_length=20, blank=True)
    parent_name = models.CharField(max_length=200, blank=True)
    parent_email = models.EmailField(blank=True)
    parent_phone = models.CharField(max_length=20, blank=True)
    address = models.TextField(blank=True)
    section = models.ForeignKey(
        Section,
        on_delete=models.CASCADE,
        related_name='students',
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='created_students',
    )

    class Meta:
        ordering = ['roll_number']
        unique_together = ['section', 'roll_number']

    def __str__(self):
        return f"{self.roll_number} - {self.name}"


class MakeUpClass(models.Model):
    """Faculty-scheduled make-up class."""
    section = models.ForeignKey(
        Section,
        on_delete=models.CASCADE,
        related_name='make_up_classes',
    )
    scheduled_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='scheduled_make_up_classes',
    )
    scheduled_date = models.DateField()
    start_time = models.TimeField()
    end_time = models.TimeField()
    classroom = models.ForeignKey(
        Classroom,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='make_up_classes',
    )
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-scheduled_date', '-start_time']

    def __str__(self):
        return f"{self.section} - {self.scheduled_date}"


class RemedialCode(models.Model):
    """One-time code for make-up attendance marking."""
    make_up_class = models.ForeignKey(
        MakeUpClass,
        on_delete=models.CASCADE,
        related_name='remedial_codes',
    )
    code = models.CharField(max_length=20, unique=True)
    expires_at = models.DateTimeField()
    is_used = models.BooleanField(default=False)

    class Meta:
        ordering = ['-expires_at']

    def __str__(self):
        return f"{self.code} ({self.make_up_class})"


class AttendanceRecord(models.Model):
    """Attendance record for a student on a given date."""
    RECORD_TYPE_CHOICES = [
        ('regular', 'Regular'),
        ('make_up', 'Make-up'),
    ]
    STATUS_CHOICES = [
        ('present', 'Present'),
        ('absent', 'Absent'),
    ]
    student = models.ForeignKey(
        Student,
        on_delete=models.CASCADE,
        related_name='attendance_records',
    )
    date = models.DateField()
    status = models.CharField(max_length=10, choices=STATUS_CHOICES)
    record_type = models.CharField(
        max_length=10,
        choices=RECORD_TYPE_CHOICES,
        default='regular',
    )
    remedial_code = models.ForeignKey(
        RemedialCode,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='attendance_records',
    )
    marked_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='marked_attendance_records',
    )
    marked_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-date', 'student__roll_number']
        constraints = [
            models.UniqueConstraint(
                fields=['student', 'date'],
                condition=Q(remedial_code__isnull=True),
                name='unique_regular_attendance',
            ),
            models.UniqueConstraint(
                fields=['student', 'remedial_code'],
                condition=Q(remedial_code__isnull=False),
                name='unique_makeup_attendance',
            ),
        ]

    def __str__(self):
        return f"{self.student} - {self.date} - {self.status}"
