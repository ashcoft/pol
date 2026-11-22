'use strict';

const test = require('node:test');
const assert = require('node:assert/strict');

const {
    safeUrl, htmlToText, imageUrls, previewItems, renderItems
} = require('../../frontend/frontend/assets/frontend/js/preview.js');

function fakeDocument() {
    function createElement(tag) {
        return {
            tag: tag,
            children: [],
            attrs: {},
            textContent: '',
            innerHTML: '',
            setAttribute(name, value) {
                this.attrs[name] = value;
            },
            appendChild(child) {
                this.children.push(child);
                return child;
            }
        };
    }
    return { createElement: createElement };
}

test('safeUrl keeps http and https links', () => {
    assert.equal(safeUrl('https://example.com/a'), 'https://example.com/a');
    assert.equal(safeUrl('http://example.com/a'), 'http://example.com/a');
});

test('safeUrl rejects file and javascript links', () => {
    assert.equal(safeUrl('file:///etc/passwd'), '');
    assert.equal(safeUrl('javascript:alert(1)'), '');
    assert.equal(safeUrl(''), '');
});

test('htmlToText strips markup and decodes entities', () => {
    assert.equal(htmlToText('<p>Hello &amp; bye</p>'), 'Hello & bye');
    assert.equal(htmlToText('a < b'), 'a < b');
    assert.equal(htmlToText('<script>alert(1)</script>Safe'), 'Safe');
});

test('htmlToText keeps a space between blocks and line breaks', () => {
    assert.equal(htmlToText('<p>Hello</p><p>world</p>'), 'Hello world');
    assert.equal(htmlToText('one<br>two'), 'one two');
});

test('htmlToText ignores a quoted > inside a tag', () => {
    assert.equal(htmlToText('<p title="Score > 10">Final score</p>'), 'Final score');
});

test('htmlToText separates isolated table cells', () => {
    assert.equal(htmlToText('<tr><td>Product</td><td>Price</td></tr>'), 'Product Price');
});

test('htmlToText skips noscript fallback text', () => {
    assert.equal(
        htmlToText('<noscript><p>Please enable JavaScript</p></noscript><p>Real content</p>'),
        'Real content'
    );
});

test('htmlToText keeps inline formatting adjacent', () => {
    assert.equal(htmlToText('<b>Hello</b>, world'), 'Hello, world');
    assert.equal(htmlToText('<p>$<strong>19</strong>.99</p>'), '$19.99');
});

test('htmlToText skips HTML comments', () => {
    assert.equal(
        htmlToText("<p>Read <!-- Publisher's note -->the full story.</p>"),
        'Read the full story.'
    );
});

test('htmlToText skips template content', () => {
    assert.equal(
        htmlToText('<div><template><p>Loading…</p></template><p>Actual story</p></div>'),
        'Actual story'
    );
});

test('htmlToText skips style content containing comparison characters', () => {
    assert.equal(
        htmlToText('<style>@media (width < 600px) { .teaser { display: none } }</style>' +
            '<p>Article summary</p>'),
        'Article summary'
    );
    assert.equal(
        htmlToText('<style>.arrow::before { content: "<"; }</style><p>Story</p>'),
        'Story'
    );
});

test('htmlToText handles Unicode before a raw-text block', () => {
    assert.equal(
        htmlToText('İ'.repeat(20) + '<style>x</style><p>Story</p>'),
        'İ'.repeat(20) + ' Story'
    );
});

test('imageUrls keeps http images and rejects local or inline images', () => {
    assert.deepEqual(
        imageUrls('<img src="https://example.com/a.jpg">' +
            '<img src="file:///etc/passwd">' +
            '<img src="javascript:alert(1)">' +
            '<img src="data:image/png;base64,AAA">' +
            '<img data-src="https://example.com/b.jpg">'),
        ['https://example.com/a.jpg']
    );
});

test('renderItems makes http links anchors and shows readable text', () => {
    const doc = fakeDocument();
    const container = doc.createElement('div');
    renderItems(container, {
        items: [{
            title: '<img src=x onerror=alert(1)>',
            link: 'https://example.com/a',
            description: '<p>Hello</p>'
        }]
    }, doc);

    const heading = container.children[0];
    const anchor = heading.children[0];
    assert.equal(anchor.tag, 'a');
    assert.equal(anchor.attrs.href, 'https://example.com/a');
    assert.equal(anchor.textContent, '<img src=x onerror=alert(1)>');
    assert.equal(container.children[1].textContent, 'Hello');
});

test('renderItems adds safe images from the description', () => {
    const doc = fakeDocument();
    const container = doc.createElement('div');
    renderItems(container, {
        items: [{
            title: 'Post',
            link: 'https://example.com/a',
            description: '<img src="https://example.com/a.jpg"><p>Body</p>'
        }]
    }, doc);

    const image = container.children[1];
    assert.equal(image.tag, 'img');
    assert.equal(image.attrs.src, 'https://example.com/a.jpg');
    assert.equal(image.attrs.alt, '');
    assert.equal(container.children[2].textContent, 'Body');
});

test('renderItems never renders a file image', () => {
    const doc = fakeDocument();
    const container = doc.createElement('div');
    renderItems(container, {
        items: [{
            title: 'Post',
            link: 'https://example.com/a',
            description: '<img src="file:///etc/passwd">'
        }]
    }, doc);

    assert.equal(container.children.length, 2);
    assert.equal(container.children[1].tag, 'div');
});

test('renderItems shows blocked links as plain text', () => {
    const doc = fakeDocument();
    const container = doc.createElement('div');
    renderItems(container, {
        items: [{
            title: 'Local file',
            link: 'file:///etc/passwd',
            description: ''
        }]
    }, doc);

    const heading = container.children[0];
    assert.equal(heading.children.length, 0);
    assert.equal(heading.textContent, 'Local file');
});

test('previewItems keeps the title text unchanged', () => {
    const items = previewItems({
        items: [{ title: '<b>bold</b>', link: 'https://example.com/a', description: '' }]
    });
    assert.equal(items[0].title, '<b>bold</b>');
    assert.equal(items[0].link, 'https://example.com/a');
});

test('previewItems includes the enclosure image', () => {
    const items = previewItems({
        items: [{
            title: 'Post',
            link: 'https://example.com/a',
            description: '',
            image: 'https://example.com/a.jpg'
        }]
    });
    assert.deepEqual(items[0].images, ['https://example.com/a.jpg']);
});
