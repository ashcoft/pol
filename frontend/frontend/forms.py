from django import forms
from django.conf import settings
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm
from django.utils.text import format_lazy
from django.utils.translation import gettext_lazy as _
from lxml import etree

from .altcha import AltchaField


CAPTCHA_LABEL = _('Verification')
CAPTCHA_ERROR = _('Verification failed. Please try again.')


def _validate_xpath(value):
    if not value or not value.strip():
        return value
    try:
        etree.XPath(value)
    except etree.XPathError as exc:
        raise forms.ValidationError(_('Invalid XPath')) from exc
    return value


class IndexForm(forms.Form):
    url = forms.CharField(max_length=2000, widget=forms.TextInput(attrs={'class': 'input-xxlarge', 'placeholder': 'http://'}))
    captcha = AltchaField(
        label=CAPTCHA_LABEL,
        error_messages={'invalid': CAPTCHA_ERROR},
    )


class LoginForm(AuthenticationForm):
    captcha = AltchaField(
        label=CAPTCHA_LABEL,
        error_messages={'invalid': CAPTCHA_ERROR},
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for name in ('username', 'password'):
            self.fields[name].widget.attrs.update({'class': 'input-xlarge'})

    def clean(self):
        # Do not verify credentials until the captcha passes; this keeps the
        # login form from hashing passwords for unsolved challenges.
        if self.errors.get('captcha'):
            return self.cleaned_data
        return super().clean()


class SignUpForm(UserCreationForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for name in ('username', 'password1', 'password2'):
            self.fields[name].widget.attrs.update({'class': 'input-xlarge'})
        self.fields['username'].help_text = ''
        self.fields['password2'].help_text = ''


class FeedEditForm(forms.Form):
    """Feed settings plus one xpath input per configured field.

    The per-field inputs are added in __init__ because they mirror the rows of
    the Field table. Every field is optional: the setup wizard allows feeds with
    any subset of fields, so an absent field must stay absent when editing.
    """

    uri = forms.URLField(
        max_length=2000, label=_('Page URL'),
        widget=forms.URLInput(attrs={'class': 'input-xxlarge'}))
    feed_xpath = forms.CharField(
        max_length=2000, label=_('Post xpath'), validators=[_validate_xpath],
        widget=forms.TextInput(attrs={'class': 'input-xxlarge'}))

    def __init__(self, *args, fields=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields_list = list(fields or [])
        for field in self.fields_list:
            self.fields['xpath_%s' % field.name] = forms.CharField(
                max_length=2000, required=False,
                label=format_lazy(_('{name} xpath'), name=field.name.capitalize()),
                validators=[_validate_xpath],
                widget=forms.TextInput(attrs={'class': 'input-xxlarge'}))

    def clean_uri(self):
        uri = self.cleaned_data['uri']
        if not getattr(settings, 'READER_ALLOW_PRIVATE', False):
            from pol.reader.errors import InvalidURLError
            from pol.reader.safety import assert_public_url
            try:
                assert_public_url(uri)
            except InvalidURLError as exc:
                raise forms.ValidationError(_('This URL is not allowed.')) from exc
        return uri

    def clean(self):
        cleaned = super().clean()
        if not any(cleaned.get('xpath_%s' % field.name, '').strip()
                   for field in self.fields_list):
            raise forms.ValidationError(_('Select at least one feed field.'))
        return cleaned

    def field_rows(self):
        return [(field, self['xpath_%s' % field.name])
                for field in self.fields_list]
