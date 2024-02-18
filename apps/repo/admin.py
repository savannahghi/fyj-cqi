from django.contrib import admin

from apps.repo.models import Author, Category, Conference, Journal, Manuscript, Venue

# Register your models here.
admin.site.register(Manuscript)
admin.site.register(Journal)
admin.site.register(Category)
admin.site.register(Author)
admin.site.register(Venue)
admin.site.register(Conference)