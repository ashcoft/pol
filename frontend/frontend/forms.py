from django import forms
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm


class IndexForm(forms.Form):
    url = forms.CharField(max_length=2000, widget=forms.TextInput(attrs={'class': 'input-xxlarge', 'placeholder': 'http://'}))


class LoginForm(AuthenticationForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for name in ('username', 'password'):
            self.fields[name].widget.attrs.update({'class': 'input-xlarge'})


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
    the Field table.
    """

    uri = forms.URLField(
        max_length=2000, label='Page URL',
        widget=forms.URLInput(attrs={'class': 'input-xxlarge'}))
    feed_xpath = forms.CharField(
        max_length=2000, label='Post xpath',
        widget=forms.TextInput(attrs={'class': 'input-xxlarge'}))

    def __init__(self, *args, fields=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields_list = list(fields or [])
        for field in self.fields_list:
            self.fields['xpath_%s' % field.name] = forms.CharField(
                max_length=2000, required=field.required,
                label='%s xpath' % field.name.capitalize(),
                widget=forms.TextInput(attrs={'class': 'input-xxlarge'}))

    def field_rows(self):
        return [(field, self['xpath_%s' % field.name])
                for field in self.fields_list]
