import uuid

from django.contrib.auth.models import AbstractUser
from django.db import models

# Create your models here.

from phonenumber_field.modelfields import PhoneNumberField


class CustomUser(AbstractUser):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False, unique=True)
    phone_number = PhoneNumberField(null=True, blank=True)

    class Meta:
        ordering = ['first_name']

    def __str__(self):
        if self.phone_number:
            return self.first_name.title() + " " + self.last_name.title() + " " + str(self.phone_number) + " " + self.email
        else:
            return self.username

    def save(self, *args, **kwargs):
        """Ensure email are in the lower case"""
        self.email = self.email.lower()
        # self.username = self.username.lower()
        super(CustomUser, self).save(*args, **kwargs)
