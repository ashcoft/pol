(function (root, factory) {
    if (typeof module === 'object' && module.exports) {
        module.exports = factory();
    } else {
        root.PolPreview = factory();
    }
}(typeof window !== 'undefined' ? window : this, function () {
    'use strict';

    var ENTITIES = {
        amp: '&',
        lt: '<',
        gt: '>',
        quot: '"',
        apos: "'",
        nbsp: ' '
    };

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

    function decodeEntities(value) {
        return String(value || '').replace(/&(#x?[0-9a-fA-F]+|[a-zA-Z][a-zA-Z0-9]*);/g,
            function (match, entity) {
                if (entity.charAt(0) === '#') {
                    var code = entity.charAt(1).toLowerCase() === 'x'
                        ? parseInt(entity.slice(2), 16)
                        : parseInt(entity.slice(1), 10);
                    if (isFinite(code) && code >= 0) {
                        try {
                            return String.fromCodePoint(code);
                        } catch (ignore) {
                            return match;
                        }
                    }
                    return match;
                }
                var key = entity.toLowerCase();
                return Object.prototype.hasOwnProperty.call(ENTITIES, key)
                    ? ENTITIES[key] : match;
            });
    }

    function stripDangerousBlocks(value) {
        return String(value || '').replace(
            /<(script|style|noscript|iframe|object|embed)\b[^>]*>[\s\S]*?<\/\1\s*>/gi,
            ' ');
    }

    var SKIP_TAGS = /^(?:script|style|noscript|template|iframe|object|embed)$/;
    var BLOCK_TAGS = /^(?:p|div|h[1-6]|li|tr|td|th|blockquote|pre|section|article|header|footer|ul|ol|table|figure|figcaption)$/;

    function collectText(node) {
        var text = '';
        for (var child = node.firstChild; child; child = child.nextSibling) {
            if (child.nodeType === 3) {
                text += child.nodeValue;
            } else if (child.nodeType === 1) {
                var tag = child.nodeName.toLowerCase();
                if (SKIP_TAGS.test(tag)) {
                    continue;
                }
                if (tag === 'br') {
                    text += ' ';
                    continue;
                }
                var block = BLOCK_TAGS.test(tag);
                if (block) {
                    text += ' ';
                }
                text += collectText(child);
                if (block) {
                    text += ' ';
                }
            }
        }
        return text;
    }

    function stripTags(value) {
        var text = '';
        var inTag = false;
        var quote = '';
        var tagStart = 0;
        for (var index = 0; index < value.length; index++) {
            var char = value.charAt(index);
            if (inTag) {
                if (quote) {
                    if (char === quote) {
                        quote = '';
                    }
                } else if (char === '"' || char === "'") {
                    quote = char;
                } else if (char === '>') {
                    inTag = false;
                    text += ' ';
                }
            } else if (char === '<') {
                inTag = true;
                tagStart = index;
            } else {
                text += char;
            }
        }
        if (inTag) {
            text += value.slice(tagStart);
        }
        return text;
    }

    function htmlToText(value) {
        if (!value) {
            return '';
        }
        if (typeof DOMParser !== 'undefined') {
            try {
                // DOMParser creates an inert document, so parsing does not
                // fetch <img>/<iframe> resources before safeUrl runs.
                var documentRef = new DOMParser().parseFromString(String(value), 'text/html');
                if (!documentRef.body) {
                    return '';
                }
                return String(collectText(documentRef.body))
                    .replace(/\s+/g, ' ').trim();
            } catch (ignore) {
                // Fall back to the tag-stripping path below.
            }
        }
        return decodeEntities(stripTags(stripDangerousBlocks(value)))
            .replace(/\s+/g, ' ').trim();
    }

    function imageUrls(value) {
        if (!value) {
            return [];
        }
        var source = String(value);
        var found = [];

        function add(candidate) {
            var url = safeUrl(candidate);
            if (url && found.indexOf(url) === -1) {
                found.push(url);
            }
        }

        if (typeof DOMParser !== 'undefined') {
            try {
                // Inert document: no image or iframe request is made here.
                var documentRef = new DOMParser().parseFromString(source, 'text/html');
                var nodes = documentRef.body
                    ? documentRef.body.querySelectorAll('img[src]') : [];
                for (var index = 0; index < nodes.length; index++) {
                    add(nodes[index].getAttribute('src'));
                }
                return found;
            } catch (ignore) {
                // Fall back to the attribute scan below.
            }
        }

        var pattern = /<img\b[^>]*?\ssrc\s*=\s*(?:"([^"]*)"|'([^']*)'|([^\s>]+))/gi;
        var match;
        while ((match = pattern.exec(source)) !== null) {
            add(match[1] || match[2] || match[3] || '');
        }
        return found;
    }

    function previewItems(feed) {
        var items = (feed && feed.items) || [];
        return items.map(function (item) {
            var description = item.description || '';
            var images = imageUrls(description);
            var primary = safeUrl(item.image);
            if (primary && images.indexOf(primary) === -1) {
                images.unshift(primary);
            }
            return {
                title: item.title ? String(item.title) : String(item.link || ''),
                link: safeUrl(item.link),
                description: description,
                text: htmlToText(description),
                images: images
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

            item.images.forEach(function (image) {
                var img = documentRef.createElement('img');
                img.setAttribute('src', image);
                img.setAttribute('alt', '');
                img.setAttribute('loading', 'lazy');
                img.setAttribute('referrerpolicy', 'no-referrer');
                img.setAttribute('style', 'max-width:100%;height:auto');
                container.appendChild(img);
            });

            var body = documentRef.createElement('div');
            // Feed markup is untrusted. Show readable text; images are added
            // above only after safeUrl has restricted them to http(s).
            body.textContent = item.text;
            container.appendChild(body);
        });
    }

    return {
        safeUrl: safeUrl,
        htmlToText: htmlToText,
        imageUrls: imageUrls,
        previewItems: previewItems,
        renderItems: renderItems
    };
}));
