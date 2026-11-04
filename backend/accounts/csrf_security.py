"""Enforce Django CSRF protection on DRF anonymous and session endpoints.

DRF's APIView.as_view() is marked csrf_exempt because SessionAuthentication
normally enforces CSRF for already-authenticated requests. Login and logout
also need CSRF checks for anonymous requests. Applying @csrf_protect directly
outside DRF's csrf_exempt callable is insufficient: the middleware sees the
inner exempt attribute and skips validation. This fresh proxy deliberately
does not copy DRF's csrf_exempt attribute.
"""

from django.views.decorators.csrf import csrf_protect


def require_csrf_for_api(view):
    def protected_proxy(request, *args, **kwargs):
        return view(request, *args, **kwargs)

    protected_proxy.__name__ = view.__name__
    protected_proxy.__doc__ = view.__doc__
    return csrf_protect(protected_proxy)
