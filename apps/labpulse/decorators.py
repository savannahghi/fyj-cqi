from functools import wraps

from django.contrib import messages
from django.contrib.auth.mixins import UserPassesTestMixin
from django.shortcuts import redirect

from functools import wraps
from django.shortcuts import redirect
from django.urls import reverse_lazy


def group_required(group_names):
    """
    Custom decorator to restrict access to view functions based on group membership.

    Usage:
    @group_required(['group1', 'group2'])
    def my_view(request):
        # View logic goes here
        ...
    """

    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            # Get the user object from the request
            user = request.user

            # Check if the user is authenticated and belongs to any of the specified groups
            if user.is_authenticated and (user.is_superuser or user.groups.filter(name__in=group_names).exists()):
                # User has the required group membership or is a superuser, allow access to the view
                return view_func(request, *args, **kwargs)
            else:
                # Add a message to be displayed after the redirect
                messages.error(request, "You don't have permission to access this page.")
                # Redirect the user to a permission denied page or another appropriate URL
                return redirect('login')  # Replace 'permission_denied' with your desired URL

        return wrapper

    return decorator

class GroupRequiredMixin(UserPassesTestMixin):
    required_groups = []  # Define the required groups for your view class
    def test_func(self):
        user = self.request.user
        return user.is_authenticated and (user.is_superuser or user.groups.filter(name__in=self.required_groups).exists())

    def handle_no_permission(self):
        return redirect(reverse_lazy('login'))
