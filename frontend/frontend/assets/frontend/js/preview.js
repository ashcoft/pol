(function (root, factory) {
    if (typeof module === 'object' && module.exports) {
        module.exports = factory();
    } else {
        root.PolPreview = factory();
    }
}(typeof window !== 'undefined' ? window : this, function () {
    'use strict';

    function decodeEntity(name) {
        switch (name.toLowerCase()) {
        case 'amp':
            return '&';
        case 'lt':
            return '<';
        case 'gt':
            return '>';
        case 'quot':
            return '"';
        case 'apos':
            return "'";
        case 'nbsp':
            return ' ';
        default:
            return null;
        }
    }

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
                var decoded = decodeEntity(entity);
                return decoded === null ? match : decoded;
            });
    }

    var HIDDEN_TAGS = ['script', 'style', 'noscript', 'template',
        'iframe', 'object', 'embed', 'textarea', 'title'];
    var RAW_TEXT_TAGS = ['script', 'style', 'noscript', 'iframe', 'object',
        'textarea', 'title'];
    var BLOCK_TAGS = ['p', 'div', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6',
        'li', 'tr', 'td', 'th', 'blockquote', 'pre', 'section', 'article',
        'header', 'footer', 'ul', 'ol', 'table', 'tbody', 'thead', 'tfoot',
        'figure', 'figcaption', 'dl', 'dt', 'dd', 'address', 'aside',
        'main', 'nav', 'form', 'fieldset', 'hr'];
    var VOID_TAGS = ['area', 'base', 'br', 'col', 'embed', 'hr', 'img',
        'input', 'link', 'meta', 'param', 'source', 'track', 'wbr'];

    function inList(list, value) {
        return list.indexOf(value) !== -1;
    }

    function rawTextEndPattern(name) {
        switch (name) {
        case 'script':
            return /<\/script(?=[\s>]|$)/gi;
        case 'style':
            return /<\/style(?=[\s>]|$)/gi;
        case 'noscript':
            return /<\/noscript(?=[\s>]|$)/gi;
        case 'iframe':
            return /<\/iframe(?=[\s>]|$)/gi;
        case 'object':
            return /<\/object(?=[\s>]|$)/gi;
        case 'textarea':
            return /<\/textarea(?=[\s>]|$)/gi;
        case 'title':
            return /<\/title(?=[\s>]|$)/gi;
        default:
            return null;
        }
    }

    function findRawTextEnd(source, name, from) {
        var pattern = rawTextEndPattern(name);
        if (!pattern) {
            return -1;
        }
        pattern.lastIndex = from;
        var match = pattern.exec(source);
        if (!match) {
            return -1;
        }
        var end = source.indexOf('>', match.index);
        return end === -1 ? source.length : end + 1;
    }

    function htmlToText(value) {
        if (!value) {
            return '';
        }
        var source = String(value);
        var text = '';
        var length = source.length;
        var index = 0;
        var hiddenDepth = 0;
        var hiddenName = '';
        var hiddenNesting = 0;

        while (index < length) {
            var lt = source.indexOf('<', index);
            if (lt === -1) {
                if (!hiddenDepth) {
                    text += source.slice(index);
                }
                break;
            }
            if (lt > index && !hiddenDepth) {
                text += source.slice(index, lt);
            }

            if (source.substr(lt, 4) === '<!--') {
                var commentEnd = source.indexOf('-->', lt + 4);
                index = commentEnd === -1 ? length : commentEnd + 3;
                continue;
            }

            var quote = '';
            var pos = lt + 1;
            while (pos < length) {
                var char = source.charAt(pos);
                if (quote) {
                    if (char === quote) {
                        quote = '';
                    }
                } else if (char === '"' || char === "'") {
                    quote = char;
                } else if (char === '>') {
                    break;
                }
                pos++;
            }
            if (pos >= length) {
                if (!hiddenDepth) {
                    text += source.slice(lt);
                }
                break;
            }

            var raw = source.slice(lt + 1, pos).trim();
            var closing = raw.charAt(0) === '/';
            var selfClosing = raw.charAt(raw.length - 1) === '/';
            var body = closing ? raw.slice(1) : raw;
            var name = body.trim().split(/\s+/)[0]
                .toLowerCase().replace(/\/$/, '');
            var voidTag = inList(VOID_TAGS, name);

            if (hiddenDepth) {
                if (name === hiddenName) {
                    if (closing) {
                        hiddenNesting -= 1;
                        if (hiddenNesting === 0) {
                            hiddenDepth = 0;
                        }
                    } else if (!selfClosing && !voidTag) {
                        hiddenNesting += 1;
                    }
                }
            } else if (!closing && inList(HIDDEN_TAGS, name) && !voidTag) {
                if (inList(RAW_TEXT_TAGS, name)) {
                    var rawEnd = findRawTextEnd(source, name, pos + 1);
                    if (rawEnd === -1) {
                        index = length;
                        break;
                    }
                    index = rawEnd;
                    continue;
                }
                hiddenDepth = 1;
                hiddenName = name;
                hiddenNesting = 1;
            } else if (name === 'br' || inList(BLOCK_TAGS, name)) {
                text += ' ';
            }

            index = pos + 1;
        }

        return decodeEntities(text).replace(/\s+/g, ' ').trim();
    }

    function imageUrls(value) {
        if (!value) {
            return [];
        }
        var source = String(value);
        var found = [];

        if (typeof DOMParser !== 'undefined') {
            try {
                // Inert document: no image or iframe request is made here.
                var documentRef = new DOMParser().parseFromString(source, 'text/html');
                if (!documentRef.body) {
                    return [];
                }
                var nodes = documentRef.body.querySelectorAll('img[src]');
                for (var index = 0; index < nodes.length; index++) {
                    var src = nodes.item(index).getAttribute('src');
                    var image = safeUrl(src);
                    if (image && found.indexOf(image) === -1) {
                        found.push(image);
                    }
                }
                return found;
            } catch (ignore) {
                // Fall back to the attribute scan below.
            }
        }

        var pattern = /<img\b[^>]*?\ssrc\s*=\s*(?:"([^"]*)"|'([^']*)'|([^\s>]+))/gi;
        var match;
        while ((match = pattern.exec(source)) !== null) {
            var candidate = safeUrl(match[1] || match[2] || match[3] || '');
            if (candidate && found.indexOf(candidate) === -1) {
                found.push(candidate);
            }
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
