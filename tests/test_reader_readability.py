from pol.reader.readability import extract

from .conftest import ARTICLE


def test_extract_keeps_article_and_drops_navigation():
    result = extract(ARTICLE, 'https://example.com/post')
    assert 'full article body' in result
    assert 'Second paragraph' in result
    assert 'Home' not in result
    assert 'newsletter' not in result
    assert '<script' not in result


def test_extract_absolutizes_images():
    result = extract(ARTICLE, 'https://example.com/post')
    assert 'src="https://example.com/images/photo.jpg"' in result


def test_extract_returns_empty_for_blank_input():
    assert extract('') == ''
    assert extract('<html></html>') == ''


def test_extract_prefers_article_element():
    page = """
    <html><body>
      <div>filler</div>
      <article><p>%s</p></article>
      <div class="sidebar"><p>%s</p></div>
    </body></html>
    """ % ('Real content, with commas, and enough words. ' * 10,
           'Sidebar content, with commas, and enough words. ' * 10)
    result = extract(page, 'https://example.com/')
    assert 'Real content' in result
    assert 'Sidebar content' not in result
