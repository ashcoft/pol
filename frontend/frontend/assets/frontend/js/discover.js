(function ($) {
    'use strict';

    $(function () {
        var $button = $('#find-feeds-btn');
        if (!$button.length) {
            return;
        }

        var $input = $('input[name="url"]').first();
        var $status = $('#feed-finder-status');
        var $results = $('#feed-finder-results');
        var $overlay = $('#feed-preview-overlay');
        var $panel = $('#feed-preview-panel');
        var $panelTitle = $('#feed-preview-heading');
        var $panelBody = $('#feed-preview-body');
        var $panelFull = $('#feed-preview-full');
        var $panelCopy = $('#feed-preview-copy');
        var $toast = $('#feed-finder-toast');

        var running = false;
        var currentFeedUrl = '';
        var lastTrigger = null;
        var toastTimer = null;
        var previewRequest = null;
        var previewSeq = 0;

        function el(tag) {
            return $(document.createElement(tag));
        }

        function showToast(message) {
            $toast.text(message).addClass('is-visible');
            window.clearTimeout(toastTimer);
            toastTimer = window.setTimeout(function () {
                $toast.removeClass('is-visible');
            }, 2200);
        }

        function copyText(text) {
            function fallback() {
                var $area = el('textarea').val(text).appendTo('body').select();
                try {
                    document.execCommand('copy');
                    showToast('Copied to clipboard!');
                } catch (ignore) {
                    showToast('Could not copy the URL.');
                }
                $area.remove();
            }

            if (navigator.clipboard && navigator.clipboard.writeText) {
                navigator.clipboard.writeText(text).then(function () {
                    showToast('Copied to clipboard!');
                }, fallback);
            } else {
                fallback();
            }
        }

        // Feed content is untrusted: only http(s) destinations become links or images.
        function safeUrl(value) {
            if (!value) {
                return '';
            }
            try {
                var parsed = new URL(value, window.location.href);
                return (parsed.protocol === 'http:' || parsed.protocol === 'https:') ? parsed.href : '';
            } catch (ignore) {
                return '';
            }
        }

        function formatDate(value) {
            if (!value) {
                return '';
            }
            var date = new Date(value);
            return isNaN(date.getTime()) ? value : date.toLocaleString();
        }

        function sanitizeSummary(html) {
            var doc = new DOMParser().parseFromString('<div>' + (html || '') + '</div>', 'text/html');
            var wrapper = doc.body.firstChild || document.createElement('div');
            $(wrapper).find('script, style, iframe, object, embed, form, input, button, svg, canvas').remove();
            $(wrapper).find('*').addBack().each(function () {
                var attributes = this.attributes;
                if (!attributes) {
                    return;
                }
                for (var i = attributes.length - 1; i >= 0; i--) {
                    var name = attributes[i].name.toLowerCase();
                    var value = (attributes[i].value || '').trim().toLowerCase();
                    if (name.indexOf('on') === 0 || name === 'srcdoc' ||
                        ((name === 'href' || name === 'src') && value.indexOf('javascript:') === 0)) {
                        this.removeAttribute(attributes[i].name);
                    }
                }
            });
            return wrapper;
        }

        function renderPreview(data) {
            $panelBody.empty();
            var items = (data && data.items) || [];
            if (!items.length) {
                el('p').addClass('muted').text('No items in this feed.').appendTo($panelBody);
                return;
            }

            $.each(items, function (_index, item) {
                var $article = el('article').addClass('feed-preview-item');
                var $title = el('h4').addClass('feed-preview-item-title');

                var href = safeUrl(item.link);
                if (href) {
                    el('a').attr({
                        href: href,
                        target: '_blank',
                        rel: 'noopener noreferrer'
                    }).text(item.title || href).appendTo($title);
                } else {
                    $title.text(item.title || '(untitled)');
                }
                $article.append($title);

                if (item.date) {
                    el('div').addClass('feed-preview-meta')
                        .text(formatDate(item.date)).appendTo($article);
                }

                var image = safeUrl(item.image);
                if (image) {
                    el('img').addClass('feed-preview-image').attr({
                        src: image,
                        alt: '',
                        loading: 'lazy'
                    }).appendTo($article);
                }

                if (item.summary) {
                    // The server sanitises summaries; this is defence in depth.
                    el('div').addClass('feed-preview-summary')
                        .append($(sanitizeSummary(item.summary)).contents())
                        .appendTo($article);
                }

                $article.appendTo($panelBody);
            });
        }

        function openPreview(feed, trigger) {
            var sequence = ++previewSeq;
            if (previewRequest) {
                previewRequest.abort();
                previewRequest = null;
            }

            currentFeedUrl = feed.url;
            lastTrigger = trigger || null;
            $panelTitle.text(feed.title || feed.url);
            $panelFull.attr('href', '/read?url=' + encodeURIComponent(feed.url) + '&format=html');
            $panelBody.empty().append(el('p').addClass('muted').text('Loading feed…'));

            $overlay.addClass('is-open').attr('aria-hidden', 'false');
            $panel.addClass('is-open').attr('aria-hidden', 'false');
            $('body').addClass('feed-preview-open');
            $('#feed-preview-close').trigger('focus');

            previewRequest = $.ajax({
                url: '/api/feed-preview',
                data: {url: feed.url},
                dataType: 'json'
            }).done(function (data) {
                if (sequence !== previewSeq) {
                    return;
                }
                if (data && data.title && !feed.title) {
                    $panelTitle.text(data.title);
                }
                renderPreview(data);
            }).fail(function (xhr) {
                if (sequence !== previewSeq || xhr.statusText === 'abort') {
                    return;
                }
                var message = 'Could not load this feed.';
                try {
                    message = JSON.parse(xhr.responseText).error || message;
                } catch (ignore) {
                    // keep the generic message
                }
                $panelBody.empty().append(el('p').addClass('muted').text(message));
            }).always(function () {
                if (sequence === previewSeq) {
                    previewRequest = null;
                }
            });
        }

        function closePreview() {
            previewSeq += 1;
            if (previewRequest) {
                previewRequest.abort();
                previewRequest = null;
            }
            $panel.removeClass('is-open').attr('aria-hidden', 'true');
            $overlay.removeClass('is-open').attr('aria-hidden', 'true');
            $('body').removeClass('feed-preview-open');
            currentFeedUrl = '';
            if (lastTrigger) {
                lastTrigger.focus();
                lastTrigger = null;
            }
        }

        function panelFocusables() {
            return $panel.find('a[href], button:not([disabled]), [tabindex]:not([tabindex="-1"])')
                .filter(':visible');
        }

        function renderResults(feeds) {
            $results.empty();
            if (!feeds.length) {
                $status.text('No feeds found on this page.');
                return;
            }

            $status.text(feeds.length + ' feed(s) found:');
            var seen = {};

            $.each(feeds, function (_index, feed) {
                if (!feed || !feed.url || seen[feed.url]) {
                    return;
                }
                seen[feed.url] = true;

                var $item = el('li').addClass('feed-result');
                var $head = el('div').addClass('feed-result-head');
                el('a').addClass('feed-result-title').attr({
                    href: feed.url,
                    target: '_blank',
                    rel: 'noopener'
                }).text(feed.title || feed.url).appendTo($head);
                if (feed.type) {
                    el('span').addClass('feed-result-type').text(feed.type).appendTo($head);
                }
                $item.append($head);
                el('div').addClass('feed-result-url').text(feed.url).appendTo($item);

                var $actions = el('div').addClass('feed-result-actions');
                el('button').attr('type', 'button')
                    .addClass('btn btn-mini feed-preview-trigger')
                    .text('Preview')
                    .data('feed', feed)
                    .appendTo($actions);
                el('button').attr('type', 'button')
                    .addClass('btn btn-mini feed-copy-trigger')
                    .text('Copy')
                    .data('url', feed.url)
                    .appendTo($actions);
                el('a').addClass('btn btn-mini').attr({
                    href: feed.url,
                    target: '_blank',
                    rel: 'noopener'
                }).text('Open').appendTo($actions);
                $item.append($actions);
                $results.append($item);
            });
        }

        function runDiscovery(url, scrollToResults) {
            url = $.trim(url || '');
            if (!url) {
                $status.text('Enter a page URL first.');
                return;
            }
            if (running) {
                return;
            }

            running = true;
            $button.prop('disabled', true);
            $status.text('Looking for feeds…');
            $results.empty();

            $.ajax({
                url: '/discover',
                data: {url: url},
                dataType: 'json'
            }).done(function (data) {
                renderResults((data && data.feeds) || []);
                if (window.history && window.history.replaceState) {
                    window.history.replaceState(null, '', '?q=' + encodeURIComponent(url));
                }
                if (scrollToResults) {
                    var top = $('.feed-finder').offset().top - 20;
                    $('html, body').animate({scrollTop: top}, 300);
                }
            }).fail(function (xhr) {
                var message = 'Feed discovery failed.';
                try {
                    message = JSON.parse(xhr.responseText).error || message;
                } catch (ignore) {
                    // keep the generic message
                }
                $status.text(message);
            }).always(function () {
                running = false;
                $button.prop('disabled', false);
            });
        }

        $button.on('click', function () {
            runDiscovery($input.val(), false);
        });

        $results.on('click', '.feed-preview-trigger', function () {
            openPreview($(this).data('feed'), this);
        });

        $results.on('click', '.feed-copy-trigger', function () {
            copyText($(this).data('url'));
        });

        $('#feed-preview-close, #feed-preview-overlay').on('click', closePreview);

        $panelCopy.on('click', function () {
            if (currentFeedUrl) {
                copyText(currentFeedUrl);
            }
        });

        $(document).on('keydown', function (event) {
            if (!$panel.hasClass('is-open')) {
                return;
            }
            if (event.key === 'Escape') {
                closePreview();
                return;
            }
            if (event.key !== 'Tab') {
                return;
            }
            var $focusable = panelFocusables();
            if (!$focusable.length) {
                return;
            }
            var first = $focusable[0];
            var last = $focusable[$focusable.length - 1];
            if (event.shiftKey && document.activeElement === first) {
                event.preventDefault();
                last.focus();
            } else if (!event.shiftKey && document.activeElement === last) {
                event.preventDefault();
                first.focus();
            }
        });

        var params = new URLSearchParams(window.location.search);
        var query = params.get('q');
        if (query) {
            $input.val(query);
            runDiscovery(query, true);
        }
    });
})(jQuery);
