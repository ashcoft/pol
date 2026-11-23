import json
import urllib.error
import urllib.request
from typing import ClassVar

from django import forms
from django.conf import settings
from django.templatetags.static import static
from django.utils.html import format_html
from django.utils.safestring import mark_safe
from django.utils.translation import gettext_lazy as _


def verify(token):
    """Verify a Cap token with the self-hosted capd server."""
    if getattr(settings, 'CAP_TEST_MODE', False):
        return token == 'passed'
    if not token or not settings.CAP_SITE_KEY or not settings.CAP_SECRET:
        return False

    payload = json.dumps({
        'secret': settings.CAP_SECRET,
        'response': token,
    }).encode('utf-8')
    url = '%s/%s/siteverify' % (
        settings.CAP_API_URL.rstrip('/'), settings.CAP_SITE_KEY)
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
    def value_from_datadict(self, data, files, name):
        return data.get('cap-token') or data.get(name)

    def render(self, name, value, attrs=None, renderer=None):
        if getattr(settings, 'CAP_TEST_MODE', False):
            return mark_safe(
                '<input type="hidden" name="cap-token" value="passed">')
        endpoint = '%s/%s/' % (
            settings.CAP_PUBLIC_URL.rstrip('/'), settings.CAP_SITE_KEY)
        return format_html(
            '<script>window.CAP_CUSTOM_WASM_URL = "{}"; '
            'window.CAP_CUSTOM_HASHWX_URL = "{}";</script>'
            '<script src="{}"></script>'
            '<cap-widget data-cap-api-endpoint="{}"></cap-widget>',
            static('frontend/js/cap_wasm_bg.wasm'),
            static('frontend/js/hashwx.wasm'),
            static('frontend/js/cap.min.js'),
            endpoint,
        )


class CapField(forms.Field):
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
