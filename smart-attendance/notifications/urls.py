from django.urls import path

from . import views

urlpatterns = [
    path('api/notifications/simulate/', views.simulate_notification, name='simulate_notification'),
]
