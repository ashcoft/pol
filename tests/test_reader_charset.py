from pol.reader import charset


def test_detects_utf8_bom():
    assert charset.detect_encoding(b'\xef\xbb\xbfhello') == 'utf-8-sig'


def test_content_type_charset_wins_over_utf8_sniffing():
    assert charset.detect_encoding('café'.encode('cp1252'),
                                   'text/html; charset=windows-1252') == 'windows-1252'


def test_detects_meta_charset_and_decodes_chinese():
    body = '<html><head><meta charset="gb2312"></head><body>中文标题</body></html>'
    raw = body.encode('gb18030')
    text, encoding = charset.decode(raw, 'text/html')
    assert encoding in ('gb2312', 'gb18030')
    assert '中文标题' in text


def test_detects_xml_declaration():
    raw = '<?xml version="1.0" encoding="iso-8859-1"?><rss><title>café</title></rss>'.encode('iso-8859-1')
    assert charset.detect_encoding(raw) == 'iso-8859-1'


def test_decode_never_raises_on_broken_bytes():
    text, _encoding = charset.decode(b'\xff\xfe\x00broken')
    assert isinstance(text, str)


def test_decode_xml_removes_declaration_and_control_characters():
    raw = '<?xml version="1.0" encoding="utf-8"?><rss>\x01<title>x</title></rss>'.encode('utf-8')
    text = charset.decode_xml(raw)
    assert not text.startswith('<?xml')
    assert '\x01' not in text
    assert '<title>x</title>' in text
