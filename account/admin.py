# from django.contrib import admin
#
# from django.contrib.auth.admin import UserAdmin as AuthUserAdmin
# from django.contrib.auth.models import User
#
# from account.models import Account
#
#
# # to add custom fields
# class AccountInline(admin.StackedInline):
#     model = Account
#     can_delete = False
#     verbose_name_plural = 'Accounts'
#
#
# class CustomizedUserAdmin(AuthUserAdmin):
#     # detach additional field from user model
#     def add_view(self, *args, **kwargs):
#         self.inlines = []
#         return super(CustomizedUserAdmin, self).add_view(*args, **kwargs)
#
#     # overwrite/attach inline class to allow add new user to be able to save
#     def change_view(self, *args, **kwargs):
#         self.inlines = [AccountInline]
#         return super(CustomizedUserAdmin, self).change_view(*args, **kwargs)
#
#
# admin.site.unregister(User)
# admin.site.register(User, CustomizedUserAdmin)  # to register
# admin.site.register(Account)  # to register account

from django.contrib import admin

# Register your models here.
from django.contrib.auth.admin import UserAdmin

from account.models import NewUser

# METHOD 1:
# Register the new user
# class CustomUserAdmin(UserAdmin):
#     fieldsets = (
#         *UserAdmin.fieldsets,
#         (
#             'Additional info',
#             {
#                 "fields": (
#                     'age',
#                     'nickname'
#                 )
#             }
#         )
#
#     )

# Register model
# admin.site.register(NewUser, CustomUserAdmin)

# =====================================================================================================================

# METHOD 2
# include additional field into the personal info of user model
# Take the normal user fields
fields = list(UserAdmin.fieldsets)
# select the second items (Personal info) and add the fields
fields[1] = ('Personal Info', {'fields':('first_name', 'last_name', 'email', 'phone_number')})
# update the fields
UserAdmin.fieldsets=tuple(fields)

admin.site.register(NewUser, UserAdmin)
#

