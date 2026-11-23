import binascii
import datetime
from typing import ClassVar

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


def _verify_solution(payload):
    try:
        result = altcha.verify_solution(
            payload, hmac_secret=settings.ALTCHA_HMAC_KEY)
    except (ValueError, TypeError, KeyError, binascii.Error, OverflowError):
        return False
    return result.verified


def _parse_challenge(payload):
    try:
        return altcha.Payload.from_base64(payload)
    except (ValueError, TypeError, KeyError, binascii.Error, OverflowError):
        return None


def _consume_challenge(signature, expires_at):
    AltchaUsedChallenge.objects.filter(expires_at__lt=timezone.now()).delete()
    try:
        AltchaUsedChallenge.objects.create(
            signature=signature, expires_at=expires_at)
    except IntegrityError:
        return False
    return True


def verify(payload):
    """Verify an Altcha payload and consume its challenge exactly once."""
    if getattr(settings, 'ALTCHA_TEST_MODE', False):
        return True
    if not payload or not _verify_solution(payload):
        return False

    parsed = _parse_challenge(payload)
    if parsed is None:
        return False

    signature = parsed.challenge.signature or parsed.challenge.parameters.nonce
    if not signature:
        return False

    expires_at = parsed.challenge.parameters.expires_at
    if expires_at:
        expires_at = datetime.datetime.fromtimestamp(
            expires_at, tz=datetime.UTC)
    else:
        expires_at = timezone.now() + datetime.timedelta(
            seconds=settings.ALTCHA_TIMEOUT)

    return _consume_challenge(signature, expires_at)


class AltchaWidget(forms.HiddenInput):
    def render(self, name, value, attrs=None, renderer=None):
        if getattr(settings, 'ALTCHA_TEST_MODE', False):
            return format_html(
                '<input type="hidden" name="{}" value="passed">', name)
        return format_html(
            '<script type="module" src="{}"></script>'
            '<altcha-widget name="{}" challenge="{}" auto="onload" '
            'type="checkbox" display="standard"></altcha-widget>',
            static('frontend/js/altcha.min.js'),
            name,
            reverse('altcha_challenge'),
        )


class AltchaField(forms.Field):
    widget = AltchaWidget
    default_error_messages: ClassVar[dict] = {
        'required': _('Complete the verification first.'),
        'invalid': _('Verification failed. Please try again.'),
    }

    def validate(self, value):
        super().validate(value)
        if not verify(value):
            raise forms.ValidationError(
                self.error_messages['invalid'], code='invalid')
