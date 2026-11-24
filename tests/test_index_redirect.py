"""Tests for the index -> setup redirect (CWE-601)."""

import os
from urllib.parse import parse_qs, urlsplit

import django
from django.test import Client, override_settings

from tests.captcha_utils import captcha_data

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'frontend.frontend.settings')
django.setup()

TEST_SETTINGS = dict(ROOT_URLCONF='frontend.frontend.urls', ALLOWED_HOSTS=['testserver'], CAP_TEST_MODE=True)


@override_settings(**TEST_SETTINGS)
def test_index_redirects_to_local_setup_page():
    source = 'example.com/story?a=1&b=2#frag'
    data = {'url': source}
    data.update(captcha_data())
    response = Client().get('/en/', data)
    assert response.status_code == 302

    location = response['Location']
    parsed = urlsplit(location)
    assert parsed.scheme == '' and parsed.netloc == ''
    assert parsed.path == '/en/setup'

    # Exactly one parameter, and its decoded value is the normalized URL.
    query = parse_qs(parsed.query)
    assert list(query) == ['url']
    assert query['url'] == ['https://' + source]

    # The value is percent-encoded, so reserved characters cannot escape it.
    assert 'https://example.com' not in location
    assert '%26' in location and '%23' in location


@override_settings(**TEST_SETTINGS)
def test_index_lowercases_scheme_and_host():
    data = {'url': 'Swa.co.id/Path?Q=Value#Frag'}
    data.update(captcha_data())
    response = Client().get('/en/', data)
    assert response.status_code == 302

    query = parse_qs(urlsplit(response['Location']).query)
    assert query['url'] == ['https://swa.co.id/Path?Q=Value#Frag']


@override_settings(**TEST_SETTINGS)
def test_index_rejects_invalid_url_without_redirecting():
    data = {'url': 'javascript:alert(1)'}
    data.update(captcha_data())
    response = Client().get('/en/', data)
    assert response.status_code == 200
    assert 'Location' not in response
    assert b'Invalid url' in response.content
