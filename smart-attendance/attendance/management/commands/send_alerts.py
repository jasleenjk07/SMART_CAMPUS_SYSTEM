"""
Management command to send scheduled alerts:
- Low attendance: sections with attendance below threshold
- Expiring codes: remedial codes about to expire
- Faculty overload: faculty with excessive teaching load
"""

from datetime import timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone

from attendance.models import (
    AttendanceRecord,
    Faculty,
    RemedialCode,
    Section,
)
from notifications.services import send_faculty_alert


def check_low_attendance(lookback_days: int, threshold_pct: float, verbosity: int):
    """
    Find sections with attendance below threshold in the last lookback_days.
    Notify faculty who teach those sections.
    """
    from collections import defaultdict

    cutoff = timezone.now().date() - timedelta(days=lookback_days)
    # Only regular attendance (not make-up)
    records = (
        AttendanceRecord.objects.filter(
            record_type="regular",
            date__gte=cutoff,
        )
        .select_related("student__section", "student__section__course")
        .values("student__section", "date", "status")
    )

    # Group by (section_id, date): count present and total
    section_date_stats = defaultdict(lambda: {"present": 0, "total": 0})

    for r in records:
        if r["student__section"] is None:
            continue
        key = (r["student__section"], r["date"])
        section_date_stats[key]["total"] += 1
        if r["status"] == "present":
            section_date_stats[key]["present"] += 1

    # Compute per-section average attendance
    section_totals = defaultdict(lambda: {"present": 0, "total": 0})
    for (section_id, _), stats in section_date_stats.items():
        section_totals[section_id]["present"] += stats["present"]
        section_totals[section_id]["total"] += stats["total"]

    low_sections = []
    for section_id, tot in section_totals.items():
        if tot["total"] == 0:
            continue
        pct = (tot["present"] / tot["total"]) * 100
        if pct < threshold_pct:
            low_sections.append((section_id, pct, tot["total"]))

    if not low_sections:
        if verbosity >= 2:
            print("  Low attendance: none found")
        return 0

    sent = 0
    section_ids = [s[0] for s in low_sections]
    sections = Section.objects.filter(id__in=section_ids).select_related("course")
    section_map = {s.id: s for s in sections}

    for section_id, pct, total in low_sections:
        section = section_map.get(section_id)
        if not section:
            continue
        # Get faculty teaching this course
        faculty_users = Faculty.objects.filter(
            course_assignments__course=section.course
        ).select_related("user")
        for faculty in faculty_users:
            email = faculty.user.email or f"{faculty.user.username}@example.com"
            msg = (
                f"Section {section} has low attendance: {pct:.1f}% "
                f"({total} records in the last {lookback_days} days). "
                "Consider follow-up with students."
            )
            send_faculty_alert(
                email=email,
                subject="Low Attendance Alert",
                message=msg,
            )
            sent += 1
            if verbosity >= 2:
                print(f"  Low attendance: notified {faculty} for {section} ({pct:.1f}%)")

    return sent


def check_expiring_codes(minutes_ahead: int, verbosity: int):
    """
    Find remedial codes expiring within minutes_ahead. Notify faculty who scheduled
    the make-up class.
    """
    now = timezone.now()
    window_end = now + timedelta(minutes=minutes_ahead)
    codes = (
        RemedialCode.objects.filter(
            expires_at__gte=now,
            expires_at__lte=window_end,
            is_used=False,
        )
        .select_related("make_up_class", "make_up_class__scheduled_by")
    )

    sent = 0
    for rc in codes:
        mu = rc.make_up_class
        scheduled_by = mu.scheduled_by
        if scheduled_by:
            email = scheduled_by.email or f"{scheduled_by.username}@example.com"
        else:
            continue  # Skip if no user linked
        msg = (
            f"Remedial code {rc.code} for make-up class {mu} (section {mu.section}) "
            f"expires at {rc.expires_at.strftime('%Y-%m-%d %H:%M')}. "
            "Students must mark attendance before it expires."
        )
        send_faculty_alert(
            email=email,
            subject="Make-Up Code Expiring Soon",
            message=msg,
        )
        sent += 1
        if verbosity >= 2:
            print(f"  Expiring code: notified for {rc.code} ({mu})")

    if verbosity >= 2 and sent == 0:
        print("  Expiring codes: none found")

    return sent


def check_faculty_overload(
    max_sections: int, max_credits: int, verbosity: int
):
    """
    Find faculty with sections or credits above threshold. Notify them.
    """
    faculty = Faculty.objects.select_related("user").prefetch_related(
        "course_assignments",
        "course_assignments__course",
    )

    sent = 0
    for f in faculty:
        assignments = f.course_assignments.select_related("course").all()
        total_credits = sum((a.course.credits or 0) for a in assignments)
        sections_count = Section.objects.filter(
            course__faculty_assignments__faculty=f
        ).distinct().count()

        overloaded = False
        reasons = []
        if sections_count >= max_sections:
            overloaded = True
            reasons.append(f"{sections_count} sections (max {max_sections})")
        if total_credits >= max_credits:
            overloaded = True
            reasons.append(f"{total_credits} credits (max {max_credits})")

        if not overloaded:
            continue

        email = f.user.email or f"{f.user.username}@example.com"
        msg = (
            f"Your teaching load may be high: {', '.join(reasons)}. "
            "Consider discussing workload with administration."
        )
        send_faculty_alert(
            email=email,
            subject="Faculty Workload Warning",
            message=msg,
        )
        sent += 1
        if verbosity >= 2:
            print(f"  Overload: notified {f} ({sections_count} sections, {total_credits} credits)")

    if verbosity >= 2 and sent == 0:
        print("  Faculty overload: none found")

    return sent


class Command(BaseCommand):
    help = (
        "Send alerts for low attendance, expiring remedial codes, "
        "and faculty overload. Logs to NotificationLog (simulated)."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--low-attendance-days",
            type=int,
            default=7,
            help="Lookback days for low attendance check (default: 7)",
        )
        parser.add_argument(
            "--low-attendance-threshold",
            type=float,
            default=75.0,
            help="Attendance %% threshold below which to alert (default: 75)",
        )
        parser.add_argument(
            "--expiring-minutes",
            type=int,
            default=30,
            help="Notify when code expires within this many minutes (default: 30)",
        )
        parser.add_argument(
            "--max-sections",
            type=int,
            default=5,
            help="Faculty overload: max sections before alert (default: 5)",
        )
        parser.add_argument(
            "--max-credits",
            type=int,
            default=18,
            help="Faculty overload: max credits before alert (default: 18)",
        )
        parser.add_argument(
            "--skip-low-attendance",
            action="store_true",
            help="Skip low attendance check",
        )
        parser.add_argument(
            "--skip-expiring-codes",
            action="store_true",
            help="Skip expiring codes check",
        )
        parser.add_argument(
            "--skip-overload",
            action="store_true",
            help="Skip faculty overload check",
        )

    def handle(self, *args, **options):
        verbosity = options["verbosity"]
        total_sent = 0

        if verbosity >= 1:
            self.stdout.write("Running send_alerts...")

        if not options["skip_low_attendance"]:
            sent = check_low_attendance(
                lookback_days=options["low_attendance_days"],
                threshold_pct=options["low_attendance_threshold"],
                verbosity=verbosity,
            )
            total_sent += sent

        if not options["skip_expiring_codes"]:
            sent = check_expiring_codes(
                minutes_ahead=options["expiring_minutes"],
                verbosity=verbosity,
            )
            total_sent += sent

        if not options["skip_overload"]:
            sent = check_faculty_overload(
                max_sections=options["max_sections"],
                max_credits=options["max_credits"],
                verbosity=verbosity,
            )
            total_sent += sent

        if verbosity >= 1:
            self.stdout.write(
                self.style.SUCCESS(f"send_alerts complete. {total_sent} alert(s) sent.")
            )
