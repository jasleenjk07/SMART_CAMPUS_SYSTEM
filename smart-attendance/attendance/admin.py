from django.contrib import admin
from .models import (
    Block,
    Classroom,
    Faculty,
    FacultyCourseAssignment,
    Course,
    Section,
    ClassSchedule,
    Student,
    MakeUpClass,
    RemedialCode,
    AttendanceRecord,
)


@admin.register(Block)
class BlockAdmin(admin.ModelAdmin):
    list_display = ('code', 'name')
    search_fields = ('code', 'name')


@admin.register(Classroom)
class ClassroomAdmin(admin.ModelAdmin):
    list_display = ('room_number', 'name', 'block', 'capacity')
    list_filter = ('block',)
    search_fields = ('name', 'room_number')


@admin.register(FacultyCourseAssignment)
class FacultyCourseAssignmentAdmin(admin.ModelAdmin):
    list_display = ('faculty', 'course')
    list_filter = ('course', 'faculty__department')
    search_fields = ('faculty__user__username', 'course__code')


@admin.register(ClassSchedule)
class ClassScheduleAdmin(admin.ModelAdmin):
    list_display = ('section', 'classroom', 'get_day_display', 'start_time', 'end_time')

    def get_day_display(self, obj):
        return obj.get_day_of_week_display()
    get_day_display.short_description = 'Day'
    list_filter = ('day_of_week', 'classroom__block')
    search_fields = ('section__name', 'classroom__name')


@admin.register(MakeUpClass)
class MakeUpClassAdmin(admin.ModelAdmin):
    list_display = ('section', 'scheduled_date', 'start_time', 'end_time', 'classroom', 'scheduled_by')
    list_filter = ('scheduled_date', 'section__course')
    search_fields = ('section__name', 'notes')
    date_hierarchy = 'scheduled_date'


@admin.register(RemedialCode)
class RemedialCodeAdmin(admin.ModelAdmin):
    list_display = ('code', 'make_up_class', 'expires_at', 'is_used')
    list_filter = ('is_used',)
    search_fields = ('code',)
    list_select_related = ('make_up_class',)


admin.site.register(Faculty)
admin.site.register(Course)
admin.site.register(Section)
admin.site.register(Student)
admin.site.register(AttendanceRecord)
