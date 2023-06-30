from functools import wraps

from django.shortcuts import redirect

from apps.fyj_mentorship.models import FyjStaffDetails


def check_fyj_staff_details_exists(view_func):
    def wrapper(request, *args, **kwargs):
        name_id = request.user.id
        existing_record = FyjStaffDetails.objects.filter(name__id=name_id).first()
        if existing_record:
            return view_func(request, *args, **kwargs)
        else:
            return redirect("add_fyj_staff_details")

    return wrapper

def require_full_name(view_func):
    @wraps(view_func)
    def wrapped_view(request, *args, **kwargs):
        if not request.user.first_name or not request.user.last_name:
            return redirect("profile")
        return view_func(request, *args, **kwargs)
    return wrapped_view