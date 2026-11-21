"""Tests for bot-protection handling and upstream error responses."""

import os
import sys

import brotli
import pytest
from scrapy.http import Headers, TextResponse

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from pol.server import Downloader


class FakeRequest:
    def __init__(self):
        self.code = None
        self.headers = {}
        self.body = b''
        self.finish_count = 0
        self.client = type('Client', (), {'host': '127.0.0.1'})()

    def setResponseCode(self, code):
        self.code = code

    def setHeader(self, key, value):
        self.headers[key] = value

    def write(self, data):
        self.body += data

    def finish(self):
        self.finish_count += 1

    def getHeader(self, name):
        return None


def make_downloader(feed_config=None, feed=None, request=None):
    return Downloader(
        feed, False, None, None, None, request or FakeRequest(), 'https://example.com/',
        feed_config, None, False, 0)


def html_response(body, status=200):
    return TextResponse(
        url='https://example.com/', status=status,
        headers=Headers({b'Content-Type': b'text/html; charset=utf-8'}), body=body)


def test_detects_cloudflare_challenge_title():
    body = b'<html><head><title>Just a moment...</title></head><body></body></html>'
    assert make_downloader()._is_bot_challenge(body)


def test_detects_challenge_structure():
    body = b'<html><body><div id="cf-challenge-running"></div></body></html>'
    assert make_downloader()._is_bot_challenge(body)


def test_article_quoting_a_challenge_phrase_is_not_blocked():
    body = (b'<html><head><title>Interview</title></head><body>'
            b'<p>He waited and said: Just a moment...</p></body></html>')
    assert not make_downloader()._is_bot_challenge(body)


def test_page_with_javascript_detections_is_not_blocked():
    body = (b'<html><head><title>News</title></head><body>'
            b'<script src="/cdn-cgi/challenge-platform/scripts/jsd/api.js"></script>'
            b'</body></html>')
    assert not make_downloader()._is_bot_challenge(body)


def test_challenge_preview_returns_502_once():
    request = FakeRequest()
    downloader = make_downloader(request=request)
    downloader.writeResponse(html_response(
        b'<html><head><title>Just a moment...</title></head></html>'))

    assert request.code == 502
    assert b'blocks automated access' in request.body
    assert request.finish_count == 1


def test_upstream_404_is_propagated():
    request = FakeRequest()
    downloader = make_downloader(request=request)
    downloader.writeResponse(html_response(b'<html><body>missing</body></html>', status=404))

    assert request.code == 404
    assert b'HTTP 404' in request.body
    assert b'not found' in request.body
    assert request.finish_count == 1


def test_normal_page_still_renders():
    request = FakeRequest()
    downloader = make_downloader(request=request)
    downloader.writeResponse(html_response(
        b'<html><head><title>News</title></head><body><p>hello</p></body></html>'))

    assert b'tag-id' in request.body
    assert request.finish_count == 1


def test_challenge_is_not_built_into_a_feed():
    class ExplodingFeed:
        def buildFeed(self, *args, **kwargs):
            raise AssertionError('buildFeed must not run for a challenge page')

    request = FakeRequest()
    downloader = make_downloader(feed_config={'id': 1}, feed=ExplodingFeed(), request=request)
    downloader.writeResponse(html_response(
        b'<html><head><title>Just a moment...</title></head></html>'))

    assert request.code == 502
    assert request.finish_count == 1


def test_brotli_decoding_is_bounded():
    downloader = make_downloader()
    assert downloader._decode_body(brotli.compress(b'x' * 1000), b'br') == b'x' * 1000

    downloader.MAX_DECOMPRESSED_SIZE = 1024
    with pytest.raises(ValueError):
        downloader._decode_body(brotli.compress(b'x' * 5000), b'br')


@pytest.mark.parametrize('status,expected', [
    (404, b'not found'),
    (403, b'refused'),
    (500, b'server error'),
    (400, b'returned an error'),
])
def test_status_details_are_specific(status, expected):
    assert expected in make_downloader()._status_detail(status).encode()
