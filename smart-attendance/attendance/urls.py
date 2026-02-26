from django.urls import path
from django.contrib.auth.views import LoginView, LogoutView

from . import views

urlpatterns = [
    path('', views.index),
    path('register/faculty/', views.faculty_register, name='faculty_register'),
    path('register/student/', views.student_register, name='student_register'),
    path('dashboard/', views.dashboard_router, name='dashboard'),
    path('dashboard/faculty/', views.faculty_dashboard, name='faculty_dashboard'),
    path('dashboard/student/', views.student_dashboard, name='student_dashboard'),
    path('dashboard/admin/', views.admin_dashboard, name='admin_dashboard'),
    path('notifications/', views.notification_logs, name='notification_logs'),
    path('faculty/', views.faculty_list, name='faculty_list'),
    path('faculty/create/', views.faculty_create, name='faculty_create'),
    path('students/', views.student_list, name='student_list'),
    path('students/create/', views.student_create, name='student_create'),
    path('students/<int:pk>/edit/', views.student_edit, name='student_edit'),
    path('sections/<int:section_id>/mark-attendance/', views.mark_attendance, name='mark_attendance'),
    path('campus-resources/', views.campus_resources, name='campus_resources'),
    path('schedule/create/', views.schedule_create, name='schedule_create'),
    path('schedule/<int:pk>/edit/', views.schedule_edit, name='schedule_edit'),
    path('schedule/<int:pk>/delete/', views.schedule_delete, name='schedule_delete'),
    path('analytics/', views.analytics_dashboard, name='analytics'),
    path('make-up/', views.makeup_list, name='makeup_list'),
    path('make-up/create/', views.makeup_create, name='makeup_create'),
    path('make-up/<int:pk>/code/', views.makeup_code, name='makeup_code'),
    path('make-up/<int:pk>/mark/', views.makeup_mark_attendance, name='makeup_mark_attendance'),
    path('make-up/mark/', views.makeup_mark, name='makeup_mark'),
    path('login/', LoginView.as_view(template_name='attendance/login.html'), name='login'),
    path('logout/', LogoutView.as_view(), name='logout'),
]
