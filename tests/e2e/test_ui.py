"""Playwright checks against a live app, downloader and nginx.

The E2E workflow starts the stack and runs this module. The tests use the
local HTTP fixture from tests/conftest.py, so they never touch the internet.
"""

import os
import re

import pytest

pytest.importorskip('playwright.sync_api')

from playwright.sync_api import expect, sync_playwright  # noqa: E402

BASE_URL = os.environ.get('E2E_BASE_URL', 'http://127.0.0.1')

FEED = """<?xml version="1.0" encoding="utf-8"?>
<rss version="2.0">
  <channel>
    <title>Example feed</title>
    <link>{base}/</link>
    <description>Example</description>
    <item>
      <title>First post</title>
      <link>{base}/article</link>
      <description>Hello from the fixture.</description>
    </item>
  </channel>
</rss>
"""


@pytest.fixture(scope='session')
def browser():
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        yield browser
        browser.close()


@pytest.fixture
def page(browser):
    context = browser.new_context()

    def _route(route):
        if route.request.url.startswith(BASE_URL):
            route.continue_()
        else:
            route.abort()

    context.route('**/*', _route)
    page = context.new_page()
    yield page
    context.close()


def _serve_discovery(http_server):
    http_server.routes.update({
        '/': (200, {'Content-Type': 'text/html'},
              '<html><head>'
              '<link rel="alternate" type="application/rss+xml" '
              'title="Example feed" href="/feed.xml">'
              '</head><body>hello</body></html>'),
        '/feed.xml': (200, {'Content-Type': 'application/rss+xml'},
                      FEED.format(base=http_server.base_url)),
        '/article': (200, {'Content-Type': 'text/html'},
                     '<html><body><h1>First post</h1>'
                     '<p>Local article for the preview.</p></body></html>'),
    })


def _wait_for_captcha(page):
    # The E2E stack sets ALTCHA_TEST_MODE=1; the widget fills the payload.
    page.wait_for_function(
        "document.querySelector('input[name=\"captcha\"]')"
        "?.value.length > 0")


def _discover(page, http_server):
    page.goto(f'{BASE_URL}/en/')
    page.fill('input[name="url"]', http_server.base_url)
    _wait_for_captcha(page)
    page.click('input[type="submit"]')
    expect(page.locator('#feed-finder-status')).to_have_text(
        re.compile('Found 1 RSS feed'))


def test_home_page_loads(page):
    page.goto(f'{BASE_URL}/en/')
    expect(page).to_have_title(re.compile('Polite'))
    expect(page.get_by_role('heading', name='RSS Finder')).to_be_visible()
    expect(page.locator('input[name="url"]')).to_be_visible()
    expect(page.locator('altcha-widget')).to_be_visible()
    expect(page.locator('input[type="submit"]')).to_be_visible()


def test_static_assets_are_served(page):
    assert page.request.get(f'{BASE_URL}/static/frontend/js/jquery.js').ok
    assert page.request.get(
        f'{BASE_URL}/static/frontend/stylesheets/application.css').ok


def test_discovery_lists_a_feed(page, http_server):
    _serve_discovery(http_server)
    _discover(page, http_server)
    expect(page.locator('.feed-result-title')).to_have_text('Example feed')


def test_preview_panel_shows_items(page, http_server):
    _serve_discovery(http_server)
    _discover(page, http_server)
    page.click('.feed-preview-trigger')
    expect(page.locator('#feed-preview-panel')).to_have_class(re.compile('is-open'))
    expect(page.locator('#feed-preview-body')).to_contain_text('First post')


def test_no_feed_opens_the_builder(page, http_server):
    http_server.routes['/'] = (
        200, {'Content-Type': 'text/html'}, '<html><body>no feeds</body></html>')
    page.goto(f'{BASE_URL}/en/')
    page.fill('input[name="url"]', http_server.base_url)
    _wait_for_captcha(page)
    page.click('input[type="submit"]')
    page.wait_for_url(re.compile(r'/setup\?url='))
    expect(page.locator('#setup-tool-string')).to_be_visible()
    expect(page.locator('#st-title')).to_be_visible()
