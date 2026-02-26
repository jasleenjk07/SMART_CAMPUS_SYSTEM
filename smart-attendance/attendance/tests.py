from datetime import time

from django.test import TestCase

from .models import Block, Classroom, ClassSchedule, Course, Section, Student
from .scheduling_service import get_room_suggestions, is_room_available


class SchedulingServiceTest(TestCase):
    """Tests for smart scheduling service: double-booking avoidance and room suggestions."""

    def setUp(self):
        block = Block.objects.create(name="Test Block", code="BLK-T")
        self.room1 = Classroom.objects.create(
            block=block, room_number="101", name="Room 101", capacity=30
        )
        self.room2 = Classroom.objects.create(
            block=block, room_number="102", name="Room 102", capacity=50
        )
        self.room3 = Classroom.objects.create(
            block=block, room_number="103", name="Room 103", capacity=20
        )
        course = Course.objects.create(name="Test Course", code="TEST101")
        self.section = Section.objects.create(course=course, name="A")
        # Add 25 students to section
        for i in range(25):
            Student.objects.create(
                section=self.section,
                roll_number=f"R{i:03d}",
                name=f"Student {i}",
            )

    def test_room_available_when_empty(self):
        """Room is available when no schedules exist."""
        self.assertTrue(
            is_room_available(self.room1, 0, time(9, 0), time(10, 0))
        )

    def test_room_unavailable_when_overlapping(self):
        """Room is unavailable when another schedule overlaps."""
        ClassSchedule.objects.create(
            section=self.section,
            classroom=self.room1,
            day_of_week=0,
            start_time=time(9, 0),
            end_time=time(10, 0),
        )
        # Same slot
        self.assertFalse(
            is_room_available(self.room1, 0, time(9, 0), time(10, 0))
        )
        # Overlapping: 9:30-10:30 overlaps 9:00-10:00
        self.assertFalse(
            is_room_available(self.room1, 0, time(9, 30), time(10, 30))
        )
        # Overlapping: 8:30-9:30 overlaps 9:00-10:00
        self.assertFalse(
            is_room_available(self.room1, 0, time(8, 30), time(9, 30))
        )

    def test_room_available_when_non_overlapping(self):
        """Room is available when existing schedule does not overlap."""
        ClassSchedule.objects.create(
            section=self.section,
            classroom=self.room1,
            day_of_week=0,
            start_time=time(9, 0),
            end_time=time(10, 0),
        )
        # Adjacent: 10:00-11:00 does not overlap 9:00-10:00
        self.assertTrue(
            is_room_available(self.room1, 0, time(10, 0), time(11, 0))
        )
        # Different day
        self.assertTrue(
            is_room_available(self.room1, 1, time(9, 0), time(10, 0))
        )

    def test_exclude_schedule_id_when_editing(self):
        """When editing, exclude the current schedule from conflict check."""
        sched = ClassSchedule.objects.create(
            section=self.section,
            classroom=self.room1,
            day_of_week=0,
            start_time=time(9, 0),
            end_time=time(10, 0),
        )
        self.assertTrue(
            is_room_available(
                self.room1, 0, time(9, 0), time(10, 0),
                exclude_schedule_id=sched.pk,
            )
        )

    def test_get_room_suggestions_avoids_double_booked(self):
        """Suggestions exclude double-booked rooms."""
        ClassSchedule.objects.create(
            section=self.section,
            classroom=self.room1,
            day_of_week=0,
            start_time=time(9, 0),
            end_time=time(10, 0),
        )
        suggestions = get_room_suggestions(
            self.section, 0, time(9, 0), time(10, 0)
        )
        classroom_ids = [s["classroom"].pk for s in suggestions]
        self.assertNotIn(self.room1.pk, classroom_ids)
        self.assertIn(self.room2.pk, classroom_ids)
        self.assertIn(self.room3.pk, classroom_ids)

    def test_get_room_suggestions_prefers_capacity(self):
        """Rooms with capacity >= section size are marked fits and ranked first."""
        suggestions = get_room_suggestions(
            self.section, 0, time(9, 0), time(10, 0)
        )
        self.assertEqual(len(suggestions), 3)
        # room1 (30), room2 (50), room3 (20) - section has 25
        # room3 (20) does not fit
        fits = [s for s in suggestions if s["fits"]]
        self.assertEqual(len(fits), 2)
        # Among fits, smaller capacity first (room1=30 before room2=50)
        self.assertEqual(fits[0]["classroom"], self.room1)
        self.assertEqual(fits[1]["classroom"], self.room2)
        self.assertFalse(suggestions[2]["fits"])
        self.assertEqual(suggestions[2]["classroom"], self.room3)
