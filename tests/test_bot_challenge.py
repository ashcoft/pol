"""Tests for bot-protection challenge detection."""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from pol.server import Downloader


def _downloader():
    return Downloader(None, False, None, None, None, None, '', None, None, False, 0)


def test_detects_cloudflare_challenge_pages():
    body = b'<html><head><title>Just a moment...</title></head><body></body></html>'
    assert _downloader()._is_bot_challenge(body)


def test_detects_challenge_platform_markup():
    body = b'<script src="/cdn-cgi/challenge-platform/h/b/orchestrate/jsch/v1"></script>'
    assert _downloader()._is_bot_challenge(body)


def test_ignores_regular_pages():
    body = b'<html><head><title>Example Domain</title></head><body><p>Hi</p></body></html>'
    assert not _downloader()._is_bot_challenge(body)
