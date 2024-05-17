from django.contrib import admin

from apps.feedback.models import App, Feedback, Response


class AppAdmin(admin.ModelAdmin):
    search_fields = ("name",)


class FeedbackAdmin(admin.ModelAdmin):
    search_fields = ("user_feedback", "app__name",
                     "created_by__username",
                     "created_by__email",
                     "created_by__phone_number",
                     )


class ResponseAdmin(admin.ModelAdmin):
    search_fields = ("response_text", "feedback__user_feedback",
                     "feedback__app__name",
                     "created_by__email",
                     "created_by__phone_number",
                     )


# Register your models here.
admin.site.register(App, AppAdmin)
admin.site.register(Feedback, FeedbackAdmin)
admin.site.register(Response, ResponseAdmin)
