from django.db import models


class NotificationLog(models.Model):
    """Stores simulated notification sends for demo/audit purposes."""

    class RecipientType(models.TextChoices):
        STUDENT = "student", "Student"
        PARENT = "parent", "Parent"
        FACULTY = "faculty", "Faculty"

    recipient_type = models.CharField(
        max_length=10,
        choices=RecipientType.choices,
    )
    recipient_email = models.EmailField()
    message = models.TextField()
    sent_at = models.DateTimeField(auto_now_add=True)
    simulated = models.BooleanField(default=True)

    class Meta:
        ordering = ["-sent_at"]
        verbose_name = "Notification Log"
        verbose_name_plural = "Notification Logs"

    def __str__(self):
        return f"{self.recipient_type}: {self.recipient_email} @ {self.sent_at}"
