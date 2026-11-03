"""Custom access decorators.

`login_required` (from Django) protects every page in this project.
`staff_required` adds one extra rule on top of it: the user must also be
marked as staff. We use it only for the manager-style actions such as
assigning a developer to a bug. Reporting a bug stays open to every
logged in user.
"""

from functools import wraps

from django.contrib import messages
from django.contrib.auth.views import redirect_to_login
from django.shortcuts import redirect


def staff_required(view_func):
    """Allow the view only for logged in users whose is_staff flag is True."""

    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        # Not logged in at all -> send them to the login page.
        if not request.user.is_authenticated:
            return redirect_to_login(request.get_full_path())

        # Logged in, but not a staff member -> explain and send them back.
        if not request.user.is_staff:
            messages.error(
                request,
                "Only staff members can do that. Ask an admin for access.",
            )
            return redirect("issue_tracker:dashboard")

        return view_func(request, *args, **kwargs)

    return _wrapped_view
