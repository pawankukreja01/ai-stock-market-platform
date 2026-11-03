"""Server-side session idle controls.

Only explicit activity POSTs refresh inactivity. Background API GETs and
page reloads never extend authenticated sessions. No provider requests.
"""
import time
from datetime import datetime, timezone as utc_timezone

from django.conf import settings
from django.contrib.auth import logout as django_logout
from django.contrib.auth.models import AnonymousUser
from django.utils import timezone


LAST_ACTIVITY_KEY = "marketpulse_last_activity"
ISSUED_AT_KEY = "marketpulse_session_issued_at"


def idle_seconds():
    return int(getattr(settings, "MARKETPULSE_IDLE_TIMEOUT_SECONDS", 1800))


def max_session_seconds():
    return int(getattr(settings, "MARKETPULSE_ABSOLUTE_SESSION_SECONDS", 43200))


def now_timestamp():
    return time.time()


def start_user_session(request):
    now = now_timestamp()
    request.session[ISSUED_AT_KEY] = now
    request.session[LAST_ACTIVITY_KEY] = now
    request.session.set_expiry(idle_seconds())


def session_deadline(request):
    session = request.session
    last = session.get(LAST_ACTIVITY_KEY)
    issued = session.get(ISSUED_AT_KEY)
    if not isinstance(last, (int, float)) or not isinstance(issued, (int, float)):
        return None
    return min(last + idle_seconds(), issued + max_session_seconds())


def session_status(request):
    deadline = session_deadline(request)
    if deadline is None:
        return None
    return {
        "expires_at": datetime.fromtimestamp(
            deadline, tz=utc_timezone.utc
        ).isoformat(),
        "idle_timeout_seconds": idle_seconds(),
    }


def extend_user_activity(request):
    now = now_timestamp()
    issued = request.session.get(ISSUED_AT_KEY)
    if not isinstance(issued, (int, float)) or now >= issued + max_session_seconds():
        return False
    request.session[LAST_ACTIVITY_KEY] = now
    remaining_absolute = max(1, int(issued + max_session_seconds() - now))
    request.session.set_expiry(min(idle_seconds(), remaining_absolute))
    return True


class ServerInactivityMiddleware:
    """Reject expired authenticated sessions before API authorization.

    Legacy sessions without timestamps are migrated once to an inactivity
    deadline. Their existing Django expiry remains authoritative. They
    don't get a new deadline on subsequent GET requests.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.user.is_authenticated:
            now = now_timestamp()
            last = request.session.get(LAST_ACTIVITY_KEY)
            issued = request.session.get(ISSUED_AT_KEY)
            if (not isinstance(last, (int, float))
                    or not isinstance(issued, (int, float))):
                # Existing sessions are valid only while Django's original
                # cookie/session expiry is valid. Migrate once, not per GET.
                start_user_session(request)
            elif (last > now + 30 or issued > now + 30
                  or now - last >= idle_seconds()
                  or now - issued >= max_session_seconds()):
                django_logout(request)
                request.user = AnonymousUser()
        return self.get_response(request)
