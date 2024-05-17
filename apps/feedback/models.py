from ckeditor.fields import RichTextField
from crum import get_current_user
from django.db import models

from apps.account.models import CustomUser
from apps.labpulse.models import BaseModel


# Create your models here.
class App(BaseModel):
    name = models.CharField(max_length=255, unique=True)

    def __str__(self):
        return f"{self.name}"

    class Meta:
        verbose_name_plural = "Apps_available"
        ordering = ['name']


class Feedback(BaseModel):
    app = models.ForeignKey(App, on_delete=models.CASCADE)
    user_feedback = RichTextField(null=True, blank=True)

    def __str__(self):
        return f"Feedback from {self.created_by} on {self.app.name}"

    class Meta:
        verbose_name_plural = "User feedback"
        ordering = ['app__name']


class Response(BaseModel):
    feedback = models.ForeignKey(Feedback, on_delete=models.CASCADE)
    response_text = RichTextField(null=True, blank=True)

    def __str__(self):
        return f"Response to {self.feedback} by {self.created_by.username}"
