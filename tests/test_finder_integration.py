"""Tests for the RSS Finder integration (compose service + nginx + UI link)."""

import os
import re

POL_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _read(*parts):
    path = os.path.join(POL_DIR, *parts)
    with open(path, encoding="utf-8") as f:
        return f.read()


def _compose_rssfinder_block():
    compose = _read("docker-compose.yaml")
    start = compose.index("rssfinder:")
    tail = compose[start:]
    # The service block ends where the top-level `networks:` section begins.
    end = tail.index("\nnetworks:")
    return tail[:end]


def test_compose_defines_rssfinder_service():
    compose = _read("docker-compose.yaml")
    assert re.search(r"^\s{2}rssfinder:\s*$", compose, re.M), (
        "docker-compose.yaml must define an `rssfinder` service"
    )


def test_compose_rssfinder_uses_official_image_and_port():
    block = _compose_rssfinder_block()
    assert "ghcr.io/0x2E/rss-finder" in block
    assert "3001:3000" in block, "rssfinder must publish host port 3001 -> container 3000"


def test_compose_rssfinder_joins_shared_network():
    block = _compose_rssfinder_block()
    assert "politepol-network" in block, (
        "rssfinder must be attached to politepol-network so it can be proxied"
    )


def test_nginx_redirects_finder_entry_point():
    site = _read("nginx", "default.site-example")
    assert "location = /finder" in site
    assert "3001" in site, "nginx must redirect /finder to the rssfinder service on port 3001"


def test_index_page_links_to_finder():
    index = _read("frontend", "frontend", "templates", "frontend", "index.html")
    assert '/finder' in index, "the home page must link to the RSS Finder entry point"
