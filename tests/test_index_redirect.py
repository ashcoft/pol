"""Tests for the index -> setup redirect (CWE-601)."""

import os
from urllib.parse import unquote

import django
from django.test import Client, override_settings

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'frontend.frontend.settings')
django.setup()


@override_settings(ROOT_URLCONF='frontend.frontend.urls')
def test_index_redirects_to_local_setup_page():
    response = Client().get('/en/', {'url': 'example.com/story'})
    assert response.status_code == 302
    location = response['Location']
    assert location.startswith('/en/setup?url=')
    # The user value is only an encoded query parameter, never the host.
    assert location.split('?', 1)[1].startswith('url=')
    assert 'example.com/story' in unquote(location)


@override_settings(ROOT_URLCONF='frontend.frontend.urls')
def test_index_rejects_invalid_url_without_redirecting():
    response = Client().get('/en/', {'url': 'javascript:alert(1)'})
    assert response.status_code == 200
