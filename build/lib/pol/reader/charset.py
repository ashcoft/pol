"""Charset detection and recovery for broken feeds and pages."""

from __future__ import annotations

import codecs
import re

_BOMS = (
    (codecs.BOM_UTF32_LE, 'utf-32'),
    (codecs.BOM_UTF32_BE, 'utf-32'),
    (codecs.BOM_UTF8, 'utf-8-sig'),
    (codecs.BOM_UTF16_LE, 'utf-16'),
    (codecs.BOM_UTF16_BE, 'utf-16'),
)
_META_RE = re.compile(
    rb'<meta[^>]+charset\s*=\s*["\']?\s*([a-zA-Z0-9_.:-]+)', re.IGNORECASE)
_XML_DECL_RE = re.compile(
    rb'<\?xml[^>]+encoding\s*=\s*["\']([^"\']+)', re.IGNORECASE)
_XML_DECL_LINE_RE = re.compile(r'^\s*<\?xml[^>]*\?>', re.IGNORECASE)
_CONTENT_TYPE_RE = re.compile(r'charset\s*=\s*["\']?([^;"\'\s]+)', re.IGNORECASE)

# Tried in order when nothing declares an encoding. Covers the usual
# legacy encodings that show up in feeds (Chinese, Japanese, Korean, Cyrillic).
_FALLBACK_ENCODINGS = (
    'utf-8', 'gb18030', 'big5', 'shift_jis', 'euc-jp', 'euc-kr',
    'cp1251', 'koi8-r', 'iso-8859-2', 'iso-8859-15', 'cp1252', 'latin-1',
)


def _valid(encoding: str | None) -> str | None:
    if not encoding:
        return None
    try:
        codecs.lookup(encoding)
    except LookupError:
        return None
    return encoding


def charset_from_content_type(content_type: str | None) -> str | None:
    if not content_type:
        return None
    match = _CONTENT_TYPE_RE.search(content_type)
    return _valid(match.group(1)) if match else None


def detect_encoding(data: bytes, content_type: str | None = None) -> str:
    """Best-effort encoding detection for a byte string."""
    if not data:
        return 'utf-8'

    for bom, encoding in _BOMS:
        if data.startswith(bom):
            return encoding

    declared = charset_from_content_type(content_type)
    if declared:
        return declared

    head = data[:4096]
    match = _XML_DECL_RE.search(head)
    if match:
        declared = _valid(match.group(1).decode('ascii', 'ignore'))
        if declared:
            return declared

    match = _META_RE.search(head)
    if match:
        declared = _valid(match.group(1).decode('ascii', 'ignore'))
        if declared:
            return declared

    try:
        data.decode('utf-8')
        return 'utf-8'
    except UnicodeDecodeError:
        pass

    guessed = _guess_with_library(data)
    return guessed or 'utf-8'


def _guess_with_library(data: bytes) -> str | None:
    try:
        from charset_normalizer import from_bytes
    except ImportError:
        pass
    else:
        best = from_bytes(data[:200000]).best()
        if best and best.encoding:
            return _valid(best.encoding)

    try:
        import chardet
    except ImportError:
        return None
    result = chardet.detect(data[:200000])
    return _valid(result.get('encoding'))


def decode(data: bytes, content_type: str | None = None) -> tuple[str, str]:
    """Decode bytes, falling back to progressively more permissive codecs.

    Returns ``(text, encoding)``. Unknown or broken declarations never raise;
    undecodable bytes are replaced instead of failing the whole document.
    """
    encoding = detect_encoding(data, content_type)
    candidates = [encoding] + [enc for enc in _FALLBACK_ENCODINGS if enc != encoding]

    for candidate in candidates:
        if not candidate:
            continue
        try:
            return data.decode(candidate), candidate
        except (UnicodeDecodeError, LookupError):
            continue

    return data.decode('utf-8', 'replace'), 'utf-8'


def strip_declaration(text: str) -> str:
    """Remove a leading XML declaration so lxml does not re-decode the text."""
    return _XML_DECL_LINE_RE.sub('', text.lstrip('\ufeff'), count=1).lstrip()


def decode_xml(data: bytes, content_type: str | None = None) -> str:
    """Decode an XML document and drop the declaration that may now be wrong."""
    text, _encoding = decode(data, content_type)
    # Control characters are illegal in XML 1.0 and abort lxml even in
    # recovery mode, so remove them before parsing.
    text = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f]', '', text)
    return strip_declaration(text)
