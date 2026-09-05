"""CI sanity tests for the pol downloader core and path-guard logic."""

import os

import pytest


def test_server_module_imports():
    # Importing pol.server pulls in scrapy/twisted/lxml wiring and exercises
    # the compression-middleware imports (regression: DecompressionMiddleware
    # was removed in modern Scrapy).
    import pol.server  # noqa: F401


def test_log_module_imports():
    import pol.log  # noqa: F401


def test_snapshot_path_guard_rejects_traversal(tmp_path, monkeypatch):
    import frontend.frontend.settings as settings
    import frontend.frontend.setup_tool_ext as ext

    base = str(tmp_path)
    monkeypatch.setattr(settings, "SNAPSHOT_DIR", base)
    monkeypatch.setattr(ext, "SNAPSHOT_DIR", base)

    hexpart = "a" * 32
    attacked_values = [
        "../outside",
        "/etc/passwd",
        hexpart + "/../../outside",
        hexpart + "/../sibling",
    ]
    for name in attacked_values:
        if os.path.isabs(name):
            resolved = os.path.realpath(name)
        else:
            resolved = os.path.realpath(os.path.join(base, name))
        # Only assert values that truly resolve outside the snapshot dir.
        if not resolved.startswith(os.path.realpath(base) + os.path.sep):
            with pytest.raises(ValueError):
                ext.build_xpath_results(["", {"999": ["", False]}], name)
        else:
            # Values that resolve inside must NOT raise the guard.
            with open(resolved, "w") as f:
                f.write("header\n\n<body>x</body>\n")
            ext.build_xpath_results(["", {"999": ["", False]}], name)


def test_snapshot_path_guard_accepts_valid_name(tmp_path, monkeypatch):
    import frontend.frontend.settings as settings
    import frontend.frontend.setup_tool_ext as ext

    base = str(tmp_path)
    monkeypatch.setattr(settings, "SNAPSHOT_DIR", base)
    monkeypatch.setattr(ext, "SNAPSHOT_DIR", base)

    # A valid snapshot file with a standard two-paragraph body.
    fname = "1234567890.123_" + ("b" * 32)
    os.makedirs(os.path.join(base, os.path.dirname(fname) or ""), exist_ok=True)
    with open(os.path.join(base, fname), "w") as f:
        f.write("header line\n\n<body>content</body>\n")

    result = ext.build_xpath_results(["//no-such-element", {"999": ["//no-such-element", False]}], fname)
    assert result is not None
    messages, posts, success = result
    assert success is True
    assert posts == []  # no elements match the xpath, so nothing is extracted
    feed_result, field_results = messages
    assert feed_result["count"] == 0