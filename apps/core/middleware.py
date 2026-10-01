from django.conf import settings
from django.contrib.auth.views import redirect_to_login
from django.urls import Resolver404, resolve


class LoginRequiredMiddleware:
    """Locks down the whole site by default.

    Only the paths/url-names listed in settings.LOGIN_EXEMPT_PREFIXES /
    LOGIN_EXEMPT_URL_NAMES are reachable without an authenticated session —
    this is an internal-only ERP tool with no public pages.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if not request.user.is_authenticated and not self._is_exempt(request):
            return redirect_to_login(request.get_full_path(), login_url=settings.LOGIN_URL)
        return self.get_response(request)

    @staticmethod
    def _is_exempt(request):
        path = request.path_info
        for prefix in settings.LOGIN_EXEMPT_PREFIXES:
            if path.startswith(prefix):
                return True
        try:
            match = resolve(path)
        except Resolver404:
            return False
        return match.view_name in settings.LOGIN_EXEMPT_URL_NAMES
