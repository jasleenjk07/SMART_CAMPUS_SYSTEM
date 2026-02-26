"""
Management command to seed the database with sample data for testing.

Creates faculty users, courses, sections, students with full contact info,
blocks, classrooms, faculty-course assignments, and class schedules.
"""

from datetime import time

from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from attendance.models import (
    Block,
    Classroom,
    ClassSchedule,
    Course,
    Faculty,
    FacultyCourseAssignment,
    Section,
    Student,
)

User = get_user_model()

# Seed data identifiers for --clear
SEED_FACULTY_USERNAMES = ["faculty1", "faculty2"]
SEED_COURSE_CODES = ["CS101", "MATH201"]
SEED_SECTION_NAMES = [("CS101", "A"), ("CS101", "B"), ("MATH201", "A")]
SEED_BLOCK_CODES = ["BLK-A", "BLK-B"]
# (block_code, room_number, name, capacity)
SEED_CLASSROOMS = [
    ("BLK-A", "101", "Main Hall", 40),
    ("BLK-A", "102", "Lab A", 35),
    ("BLK-A", "103", "Seminar Room", 30),
    ("BLK-B", "201", "Science Lab", 50),
    ("BLK-B", "202", "Math Room", 30),
]
# (course_code, section_name, block_code, room_number, day_of_week, start_time, end_time)
# day_of_week: 0=Mon, 1=Tue, 2=Wed, 3=Thu, 4=Fri
SEED_CLASS_SCHEDULES = [
    ("CS101", "A", "BLK-A", "101", 0, time(9, 0), time(10, 0)),   # Mon 9-10
    ("CS101", "A", "BLK-A", "101", 2, time(9, 0), time(10, 0)),   # Wed 9-10
    ("CS101", "B", "BLK-A", "102", 1, time(9, 0), time(10, 0)),   # Tue 9-10
    ("CS101", "B", "BLK-A", "102", 3, time(9, 0), time(10, 0)),   # Thu 9-10
    ("MATH201", "A", "BLK-B", "201", 0, time(11, 0), time(12, 0)),  # Mon 11-12
    ("MATH201", "A", "BLK-B", "201", 2, time(11, 0), time(12, 0)),  # Wed 11-12
]

# Sample students: (roll_number, name, email, phone, parent_name, parent_email, parent_phone, address)
SEED_STUDENTS_CS101A = [
    ("R001", "Alice Johnson", "alice.johnson@example.com", "+1-555-0101", "John Johnson", "john.j@example.com", "+1-555-0102", "123 Main St, City"),
    ("R002", "Bob Smith", "bob.smith@example.com", "+1-555-0201", "Jane Smith", "jane.s@example.com", "+1-555-0202", "456 Oak Ave, Town"),
    ("R003", "Carol Williams", "carol.w@example.com", "+1-555-0301", "Bill Williams", "bill.w@example.com", "+1-555-0302", "789 Pine Rd, Village"),
    ("R004", "David Brown", "david.brown@example.com", "+1-555-0401", "Sarah Brown", "sarah.b@example.com", "+1-555-0402", "321 Elm St, Borough"),
    ("R005", "Eva Davis", "eva.davis@example.com", "+1-555-0501", "Mike Davis", "mike.d@example.com", "+1-555-0502", "654 Maple Dr, Hamlet"),
]

SEED_STUDENTS_CS101B = [
    ("R006", "Frank Miller", "frank.m@example.com", "+1-555-0601", "Lisa Miller", "lisa.m@example.com", "+1-555-0602", "987 Cedar Ln, County"),
    ("R007", "Grace Lee", "grace.lee@example.com", "+1-555-0701", "Tom Lee", "tom.lee@example.com", "+1-555-0702", "147 Birch St, District"),
    ("R008", "Henry Wilson", "henry.w@example.com", "+1-555-0801", "Amy Wilson", "amy.w@example.com", "+1-555-0802", "258 Spruce Ave, Region"),
]

SEED_STUDENTS_MATH201A = [
    ("R009", "Ivy Taylor", "ivy.taylor@example.com", "+1-555-0901", "Chris Taylor", "chris.t@example.com", "+1-555-0902", "369 Walnut Blvd, State"),
    ("R010", "Jack Anderson", "jack.a@example.com", "+1-555-1001", "Pat Anderson", "pat.a@example.com", "+1-555-1002", "741 Cherry Ct, Province"),
]


class Command(BaseCommand):
    help = "Seed the database with sample courses, sections, faculty, and students for testing."

    def add_arguments(self, parser):
        parser.add_argument(
            "--clear",
            action="store_true",
            help="Remove seed data before seeding (resets to empty state for seed objects).",
        )

    def handle(self, *args, **options):
        if options["clear"]:
            self._clear_seed_data()
        self._seed_data()
        self.stdout.write(self.style.SUCCESS("Seed data created successfully."))

    def _clear_seed_data(self):
        """Remove seed data (students, sections, courses, faculty, blocks, classrooms, etc.)."""
        # Delete students in seed sections
        deleted_students = Student.objects.filter(
            section__course__code__in=SEED_COURSE_CODES,
        ).delete()
        self.stdout.write(f"Deleted {deleted_students[0]} students.")

        # Delete class schedules (must be before sections so we can delete classrooms later)
        for course_code, section_name in SEED_SECTION_NAMES:
            Section.objects.filter(
                course__code=course_code, name=section_name
            ).delete()  # CASCADE deletes ClassSchedule
        self.stdout.write("Deleted seed sections and class schedules.")

        for code in SEED_COURSE_CODES:
            Course.objects.filter(code=code).delete()
        self.stdout.write("Deleted seed courses.")

        for username in SEED_FACULTY_USERNAMES:
            try:
                user = User.objects.get(username=username)
                Faculty.objects.filter(user=user).delete()
                user.delete()
                self.stdout.write(f"Deleted faculty user: {username}")
            except User.DoesNotExist:
                pass

        # Delete classrooms and blocks (ClassSchedule already gone via section CASCADE)
        for block_code, room_number, _, _ in SEED_CLASSROOMS:
            Classroom.objects.filter(block__code=block_code, room_number=room_number).delete()
        self.stdout.write("Deleted seed classrooms.")
        for code in SEED_BLOCK_CODES:
            Block.objects.filter(code=code).delete()
        self.stdout.write("Deleted seed blocks.")

    def _seed_data(self):
        """Create faculty users, courses, sections, and students."""
        # Create faculty users
        faculty_user = None
        for i, username in enumerate(SEED_FACULTY_USERNAMES):
            user, created = User.objects.get_or_create(
                username=username,
                defaults={
                    "email": f"{username}@example.com",
                    "first_name": f"Faculty",
                    "last_name": str(i + 1),
                    "is_staff": True,
                    "is_active": True,
                },
            )
            if created:
                user.set_password("testpass123")
                user.save()
                self.stdout.write(f"Created faculty user: {username} (password: testpass123)")
            faculty_user = user  # Use last faculty for created_by

            Faculty.objects.get_or_create(
                user=user,
                defaults={
                    "department": "Computer Science" if i == 0 else "Mathematics",
                    "phone": f"+1-555-{9000 + i:04d}",
                },
            )

        # Create courses
        course_cs101, _ = Course.objects.get_or_create(
            code="CS101",
            defaults={"name": "Introduction to Programming", "credits": 3},
        )
        course_math201, _ = Course.objects.get_or_create(
            code="MATH201",
            defaults={"name": "Calculus I", "credits": 4},
        )

        # Create blocks and classrooms
        block_by_code = {}
        for code, name in [("BLK-A", "Block A"), ("BLK-B", "Science Block")]:
            block, _ = Block.objects.get_or_create(code=code, defaults={"name": name})
            block_by_code[code] = block
        for block_code, room_number, name, capacity in SEED_CLASSROOMS:
            block = block_by_code[block_code]
            Classroom.objects.get_or_create(
                block=block,
                room_number=room_number,
                defaults={"name": name, "capacity": capacity},
            )
        classroom_by_block_room = {}
        for block_code, room_number, _, _ in SEED_CLASSROOMS:
            classroom_by_block_room[(block_code, room_number)] = Classroom.objects.get(
                block__code=block_code, room_number=room_number
            )

        # Create sections
        section_cs101a, _ = Section.objects.get_or_create(
            course=course_cs101,
            name="A",
            defaults={},
        )
        section_cs101b, _ = Section.objects.get_or_create(
            course=course_cs101,
            name="B",
            defaults={},
        )
        section_math201a, _ = Section.objects.get_or_create(
            course=course_math201,
            name="A",
            defaults={},
        )

        # Create faculty-course assignments
        faculty1 = Faculty.objects.get(user__username="faculty1")
        faculty2 = Faculty.objects.get(user__username="faculty2")
        FacultyCourseAssignment.objects.get_or_create(
            faculty=faculty1,
            course=course_cs101,
        )
        FacultyCourseAssignment.objects.get_or_create(
            faculty=faculty2,
            course=course_math201,
        )

        # Create class schedules
        section_by_course_name = {
            ("CS101", "A"): section_cs101a,
            ("CS101", "B"): section_cs101b,
            ("MATH201", "A"): section_math201a,
        }
        for course_code, section_name, block_code, room_number, day, start, end in SEED_CLASS_SCHEDULES:
            section = section_by_course_name[(course_code, section_name)]
            classroom = classroom_by_block_room[(block_code, room_number)]
            ClassSchedule.objects.get_or_create(
                classroom=classroom,
                day_of_week=day,
                start_time=start,
                defaults={"section": section, "end_time": end},
            )

        # Create students
        sections_students = [
            (section_cs101a, SEED_STUDENTS_CS101A),
            (section_cs101b, SEED_STUDENTS_CS101B),
            (section_math201a, SEED_STUDENTS_MATH201A),
        ]

        for section, students_data in sections_students:
            for roll_number, name, email, phone, parent_name, parent_email, parent_phone, address in students_data:
                Student.objects.get_or_create(
                    section=section,
                    roll_number=roll_number,
                    defaults={
                        "name": name,
                        "email": email,
                        "phone": phone,
                        "parent_name": parent_name,
                        "parent_email": parent_email,
                        "parent_phone": parent_phone,
                        "address": address,
                        "created_by": faculty_user,
                    },
                )

        num_students = len(SEED_STUDENTS_CS101A) + len(SEED_STUDENTS_CS101B) + len(SEED_STUDENTS_MATH201A)
        self.stdout.write(
            f"Seeded: 2 faculty users, 2 courses, 3 sections, {num_students} students, "
            f"{len(SEED_BLOCK_CODES)} blocks, {len(SEED_CLASSROOMS)} classrooms, "
            f"2 faculty-course assignments, {len(SEED_CLASS_SCHEDULES)} class schedules."
        )
