"""Cap captcha verification and Django form widget."""

import json
import urllib.error
import urllib.request
from typing import ClassVar

from django import forms
from django.conf import settings
from django.templatetags.static import static
from django.utils.html import format_html
from django.utils.translation import gettext_lazy as _

CAP_TEST_ANSWER = 'passed'


def verify(token):
    """Verify a Cap token with the self-hosted capd server."""
    if getattr(settings, 'CAP_TEST_MODE', False):
        return token == CAP_TEST_ANSWER
    if not token or not settings.CAP_SITE_KEY or not settings.CAP_SECRET:
        return False

    payload = json.dumps({
        'secret': settings.CAP_SECRET,
        'response': token,
    }).encode('utf-8')
    url = (
        f'{settings.CAP_API_URL.rstrip("/")}/'
        f'{settings.CAP_SITE_KEY}/siteverify'
    )
    request = urllib.request.Request(
        url, data=payload,
        headers={'Content-Type': 'application/json'},
        method='POST')
    try:
        with urllib.request.urlopen(request, timeout=10) as response:  # nosec B310
            data = json.loads(response.read().decode('utf-8'))
    except (urllib.error.URLError, OSError, ValueError):
        return False
    return data.get('success') is True


class CapWidget(forms.Widget):
    """Render the Cap widget and read its hidden cap-token field."""

    def value_from_datadict(self, data, files, name):
        """Return the token added by the Cap widget."""
        return data.get('cap-token') or data.get(name)

    def render(self, name, value, attrs=None, renderer=None):
        """Render the Cap widget or the test-mode token input."""
        if getattr(settings, 'CAP_TEST_MODE', False):
            return format_html(
                '<input type="hidden" name="cap-token" value="{}">',
                CAP_TEST_ANSWER)
        endpoint = (
            f'{settings.CAP_PUBLIC_URL.rstrip("/")}/'
            f'{settings.CAP_SITE_KEY}/'
        )
        return format_html(
            '<script>window.CAP_CUSTOM_WASM_URL = "{}"; '
            'window.CAP_CUSTOM_HASHWX_URL = "{}";</script>'
            '<script src="{}"></script>'
            '<cap-widget data-cap-api-endpoint="{}" required></cap-widget>',
            static('frontend/js/cap_wasm_bg.wasm'),
            static('frontend/js/hashwx.wasm'),
            static('frontend/js/cap.min.js'),
            endpoint,
        )


class CapField(forms.Field):
    """Form field that verifies a Cap token with capd."""

    widget = CapWidget
    default_error_messages: ClassVar[dict] = {
        'required': _('Complete the verification first.'),
        'invalid': _('Verification failed. Please try again.'),
    }

    def validate(self, value):
        super().validate(value)
        if not verify(value):
            raise forms.ValidationError(
                self.error_messages['invalid'], code='invalid')
