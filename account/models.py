from django.contrib.auth.models import AbstractUser
from django.db import models

# Create your models here.

from phonenumber_field.modelfields import PhoneNumberField


class NewUser(AbstractUser):
    phone_number = PhoneNumberField(null=True, blank=True)

    def __str__(self):
        return self.username

    def save(self, *args, **kwargs):
        """Ensure username and email are in the right case"""
        self.email = self.email.lower()
        super(NewUser, self).save(*args, **kwargs)
