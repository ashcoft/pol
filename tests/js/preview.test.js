'use strict';

const test = require('node:test');
const assert = require('node:assert/strict');

const { safeUrl, previewItems, renderItems } = require(
    '../../frontend/frontend/assets/frontend/js/preview.js'
);

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

test('renderItems makes http links anchors and keeps titles as text', () => {
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
    assert.equal(container.children[1].textContent, '<p>Hello</p>');
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
