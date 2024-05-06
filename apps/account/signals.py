from django.conf import settings
from django.conf.global_settings import EMAIL_HOST_USER
from django.contrib.auth.tokens import default_token_generator
from django.core.mail import send_mail
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode

from apps.account.models import CustomUser


@receiver(post_save, sender=CustomUser)
def send_user_created_email(sender, instance, created, **kwargs):
    if created:
        subject = 'Your account has been created'
        url="https://cqi.fahariyajamii.org/"

        # Generate password reset link
        uid = urlsafe_base64_encode(force_bytes(instance))
        token = default_token_generator.make_token(instance)
        password_reset_url = f'https://cqi.fahariyajamii.org/password-reset/{uid}/{token}/'
        password_reset_url = f'http://localhost:8000/password-reset/{uid}/{token}/'
        message = f"""
            <html>
                <body>
                    <p>Hi,</p>
                    <p>Your account has been created on our platform. Here are your credentials:</p>
                    <ul>
                        <li><b>Username: </b> {instance.username}</li>
                        <li><b>Password: </b> {instance._password}</li>
                    </ul>
                    <p>Once you login, please change your username to your liking.</p>
                    <p><a href="{url}">Click here to login</a></p>
                    <p><a href="{password_reset_url}">Click here to reset your password</a></p>
                    <p>Best regards,</p>
                    <p>Peter</p>
                    <p>Quality Improvement Specialist</p>
                </body>
            </html>
            """

        send_mail(subject, message, EMAIL_HOST_USER, [instance.username], html_message=message)
