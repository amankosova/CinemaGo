from functools import wraps

from django.contrib.auth.decorators import login_required
from django.shortcuts import render


def staff_required(view):
    @wraps(view)
    @login_required
    def wrapper(request, *args, **kwargs):
        if not request.user.is_staff:
            return render(request, "403.html", status=403)
        return view(request, *args, **kwargs)

    return wrapper
