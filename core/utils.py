"""Small helpers shared by cart / wishlist / orders views."""
from functools import wraps

from django.contrib import messages
from django.contrib.auth.views import redirect_to_login
from django.http import JsonResponse
from django.shortcuts import redirect
from django.urls import reverse
from django.utils.http import url_has_allowed_host_and_scheme


def is_ajax(request):
    return request.headers.get('x-requested-with') == 'XMLHttpRequest'


def safe_next(request, default='home'):
    """Return a safe URL to go back to (never an external site)."""
    target = request.POST.get('next') or request.META.get('HTTP_REFERER') or ''
    if target and url_has_allowed_host_and_scheme(target, {request.get_host()}):
        return target
    return reverse(default)


def shop_login_required(view):
    """Like @login_required, but answers JavaScript (AJAX) calls with JSON."""
    @wraps(view)
    def wrapper(request, *args, **kwargs):
        if request.user.is_authenticated:
            return view(request, *args, **kwargs)
        login_url = reverse('login')
        if is_ajax(request):
            return JsonResponse({'ok': False, 'message': 'Please login to continue.',
                                 'login_url': login_url}, status=401)
        messages.info(request, 'Please login to continue.')
        return redirect_to_login(safe_next(request), login_url)
    return wrapper


def respond(request, ok, message, redirect_to=None, **extra):
    """AJAX -> JSON.  Normal form post -> flash message + redirect."""
    if is_ajax(request):
        return JsonResponse({'ok': ok, 'message': message, **extra}, status=200 if ok else 400)
    (messages.success if ok else messages.error)(request, message)
    return redirect(redirect_to or safe_next(request))
