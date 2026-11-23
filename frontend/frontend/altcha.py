import datetime

import altcha
from django import forms
from django.conf import settings
from django.db import IntegrityError
from django.templatetags.static import static
from django.urls import reverse
from django.utils import timezone
from django.utils.html import format_html
from django.utils.translation import gettext_lazy as _

from .models import AltchaUsedChallenge


def create_challenge():
    return altcha.create_challenge(
        algorithm=settings.ALTCHA_ALGORITHM,
        cost=settings.ALTCHA_COST,
        expires_at=timezone.now() + datetime.timedelta(
            seconds=settings.ALTCHA_TIMEOUT),
        hmac_secret=settings.ALTCHA_HMAC_KEY,
    )


def verify(payload):
    """Verify an Altcha payload and consume its challenge exactly once."""
    if getattr(settings, 'ALTCHA_TEST_MODE', False):
        return True
    if not payload:
        return False

    try:
        result = altcha.verify_solution(
            payload, hmac_secret=settings.ALTCHA_HMAC_KEY)
    except Exception:
        return False
    if not result.verified:
        return False

    try:
        parsed = altcha.Payload.from_base64(payload)
        signature = parsed.challenge.signature or parsed.challenge.parameters.nonce
        expires_at = parsed.challenge.parameters.expires_at
    except Exception:
        return False
    if not signature:
        return False

    if expires_at:
        expires_at = datetime.datetime.fromtimestamp(
            expires_at, tz=datetime.timezone.utc)
    else:
        expires_at = timezone.now() + datetime.timedelta(
            seconds=settings.ALTCHA_TIMEOUT)

    AltchaUsedChallenge.objects.filter(expires_at__lt=timezone.now()).delete()
    try:
        AltchaUsedChallenge.objects.create(
            signature=signature, expires_at=expires_at)
    except IntegrityError:
        return False
    return True


class AltchaWidget(forms.HiddenInput):
    def render(self, name, value, attrs=None, renderer=None):
        test = ' test' if getattr(settings, 'ALTCHA_TEST_MODE', False) else ''
        return format_html(
            '<script type="module" src="{}"></script>'
            '<altcha-widget name="{}" challengeurl="{}" auto="onload" '
            'hidefooter hidelogo{}></altcha-widget>',
            static('frontend/js/altcha.min.js'),
            name,
            reverse('altcha_challenge'),
            test,
        )


class AltchaField(forms.Field):
    widget = AltchaWidget
    default_error_messages = {
        'required': _('Complete the verification first.'),
        'invalid': _('Verification failed. Please try again.'),
    }

    def validate(self, value):
        super().validate(value)
        if not verify(value):
            raise forms.ValidationError(
                self.error_messages['invalid'], code='invalid')
