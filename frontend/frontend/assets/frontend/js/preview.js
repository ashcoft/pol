(function (root, factory) {
    if (typeof module === 'object' && module.exports) {
        module.exports = factory();
    } else {
        root.PolPreview = factory();
    }
}(typeof window !== 'undefined' ? window : this, function () {
    'use strict';

    function safeUrl(value) {
        if (!value) {
            return '';
        }
        var base = (typeof window !== 'undefined' && window.location)
            ? window.location.origin
            : 'http://localhost';
        try {
            var url = new URL(value, base);
            return (url.protocol === 'http:' || url.protocol === 'https:') ? url.href : '';
        } catch (ignore) {
            return '';
        }
    }

    function previewItems(feed) {
        var items = (feed && feed.items) || [];
        return items.map(function (item) {
            return {
                title: item.title ? String(item.title) : String(item.link || ''),
                link: safeUrl(item.link),
                description: item.description || ''
            };
        });
    }

    function renderItems(container, feed, doc) {
        var documentRef = doc || (typeof document !== 'undefined' ? document : null);
        if (!container || !documentRef) {
            return;
        }
        previewItems(feed).forEach(function (item) {
            var heading = documentRef.createElement('h4');
            if (item.link) {
                var anchor = documentRef.createElement('a');
                anchor.setAttribute('href', item.link);
                anchor.textContent = item.title;
                heading.appendChild(anchor);
            } else {
                heading.textContent = item.title;
            }
            container.appendChild(heading);

            var body = documentRef.createElement('div');
            body.innerHTML = item.description;
            container.appendChild(body);
        });
    }

    return {
        safeUrl: safeUrl,
        previewItems: previewItems,
        renderItems: renderItems
    };
}));
