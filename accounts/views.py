from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render
from .forms import RegisterForm


def register(request):
    if request.user.is_authenticated:
        return redirect("home")
    if request.method == "POST":
        form = RegisterForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, "Account created successfully.")
            return redirect("home")
    else:
        form = RegisterForm()
    return render(request, "accounts/register.html", {"form": form})


@login_required
def profile(request):
    return render(request, "accounts/profile.html")


# The same generic sign-in error is shown for unknown users and bad passwords.
# A username AND request-IP scoped rate limiter avoids a universal account lock.
from datetime import timedelta
import hashlib

from django.conf import settings
from django.contrib.auth.views import LoginView
from django.db import transaction
from django.utils import timezone
from django.utils.translation import get_language
from .models import LoginAttempt

MAX_FAILURES = 5
LOCK_SECONDS = 300

LOGIN_TEXT = {
    "en": {
        "invalid": "Incorrect username or password. Please try again.",
        "locked": "Too many failed attempts. Try again in {minutes}:{seconds:02d}.",
    },
    "ru": {
        "invalid": "Неверное имя пользователя или пароль. Попробуйте ещё раз.",
        "locked": "Слишком много неудачных попыток. Повторите через {minutes}:{seconds:02d}.",
    },
    "kk": {
        "invalid": "Пайдаланушы аты немесе құпиясөз қате. Қайта көріңіз.",
        "locked": "Кіру әрекеттерінің саны асып кетті. {minutes}:{seconds:02d} кейін қайталап көріңіз.",
    },
}


def login_message(kind, remaining=0):
    language = (get_language() or 'en').split('-')[0]
    dictionary = LOGIN_TEXT.get(language, LOGIN_TEXT['en'])
    minutes, seconds = divmod(max(0, remaining), 60)
    return dictionary[kind].format(minutes=minutes, seconds=seconds)


class SecureLoginView(LoginView):
    template_name = 'accounts/login.html'

    def attempt_key(self):
        identifier = self.request.POST.get('username', '').strip().casefold()
        # Never trust unvalidated X-Forwarded-For headers from clients.
        address = self.request.META.get('REMOTE_ADDR', '')
        payload = f'{settings.SECRET_KEY}:{identifier}:{address}'.encode('utf-8')
        return hashlib.sha256(payload).hexdigest()

    def post(self, request, *args, **kwargs):
        self._attempt_key = self.attempt_key()
        attempt = LoginAttempt.objects.filter(pk=self._attempt_key).first()
        if attempt and attempt.locked_until and attempt.locked_until > timezone.now():
            seconds = max(1, int((attempt.locked_until-timezone.now()).total_seconds()) + 1)
            return self.render_to_response(self.get_context_data(
                form=self.form_class(),
                login_error=login_message('locked', seconds),
                lock_seconds=seconds,
            ), status=429)
        return super().post(request, *args, **kwargs)

    def form_invalid(self, form):
        # Only count an actual login attempt; missing form fields aren't passwords.
        if self.request.POST.get('username', '').strip() and self.request.POST.get('password'):
            with transaction.atomic():
                attempt, _ = LoginAttempt.objects.select_for_update().get_or_create(pk=self._attempt_key)
                now = timezone.now()
                if attempt.locked_until and attempt.locked_until <= now:
                    attempt.failed_count = 0
                    attempt.locked_until = None
                attempt.failed_count += 1
                if attempt.failed_count >= MAX_FAILURES:
                    attempt.locked_until = now + timedelta(seconds=LOCK_SECONDS)
                attempt.save()
            if attempt.locked_until and attempt.locked_until > now:
                return self.render_to_response(self.get_context_data(
                    form=form, login_error=login_message('locked', LOCK_SECONDS),
                    lock_seconds=LOCK_SECONDS,
                ), status=429)
        return self.render_to_response(self.get_context_data(
            form=form, login_error=login_message('invalid'),
        ), status=200)

    def form_valid(self, form):
        LoginAttempt.objects.filter(pk=self._attempt_key).delete()
        return super().form_valid(form)
