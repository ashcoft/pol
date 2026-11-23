(function ($) {
    'use strict';

    $(function () {
        var $form = $('form.rss-search-form').first();
        if (!$form.length) {
            return;
        }
        var $submit = $form.find('input[type="submit"]');

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
        var sourceFavicon = '';

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

        var FALLBACK_FAVICON = '/static/frontend/images/rss-640.png';

        function faviconUrl(value) {
            try {
                var host = new URL(value, window.location.href).hostname;
                return host
                    ? 'https://icons.duckduckgo.com/ip3/' + encodeURIComponent(host) + '.ico'
                    : '';
            } catch (ignore) {
                return '';
            }
        }

        function useFallbackIcon(image) {
            if (image.src.indexOf('rss-640') === -1) {
                image.src = FALLBACK_FAVICON;
            }
        }

        function formatDate(value) {
            if (!value) {
                return '';
            }
            var date = new Date(value);
            return isNaN(date.getTime()) ? value : date.toLocaleString();
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

                if (item.summary_text || item.summary) {
                    el('div').addClass('feed-preview-summary')
                        .text(item.summary_text || item.summary)
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
            var favicon = document.getElementById('feed-preview-favicon');
            if (favicon) {
                favicon.onerror = function () {
                    useFallbackIcon(this);
                };
                favicon.src = sourceFavicon || faviconUrl(feed.url) || FALLBACK_FAVICON;
            }
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

        function normalizeUrl(value) {
            var url = $.trim(value || '');
            if (!url) {
                return '';
            }
            if (!/^[a-z][a-z0-9+.-]*:/i.test(url)) {
                url = 'https://' + url;
            }
            var match = url.match(/^([a-z][a-z0-9+.-]*):\/\/([^/?#]*)([\s\S]*)$/i);
            if (!match) {
                return url;
            }
            var authority = match[2];
            var at = authority.lastIndexOf('@');
            var userinfo = at >= 0 ? authority.slice(0, at + 1) : '';
            var hostport = at >= 0 ? authority.slice(at + 1) : authority;
            return match[1].toLowerCase() + '://' + userinfo +
                hostport.toLowerCase() + match[3];
        }

        function openFeedBuilder(url) {
            var setupUrl = $form.data('setup-url') || '/setup';
            var target = normalizeUrl(url);
            if (!target) {
                setStatus('Enter a page URL first.');
                return;
            }
            window.location.assign(setupUrl + '?url=' + encodeURIComponent(target));
        }

        function renderResults(feeds, sourceUrl) {
            $results.empty();
            sourceFavicon = faviconUrl(sourceUrl);
            if (!feeds.length) {
                return;
            }

            setStatus('Found ' + feeds.length + ' RSS feed' + (feeds.length === 1 ? '' : 's'));
            var seen = {};

            $.each(feeds, function (_index, feed) {
                if (!feed || !feed.url || seen[feed.url]) {
                    return;
                }
                seen[feed.url] = true;

                var $item = el('li').addClass('feed-result');
                var $icon = el('img').addClass('feed-result-favicon').attr({
                    src: sourceFavicon || faviconUrl(feed.url) || FALLBACK_FAVICON,
                    alt: '',
                    width: 38,
                    height: 38,
                    loading: 'lazy',
                    referrerpolicy: 'no-referrer'
                });
                $icon[0].onerror = function () {
                    useFallbackIcon(this);
                };
                $item.append($icon);

                var $main = el('div').addClass('feed-result-main');
                var $head = el('div').addClass('feed-result-head');
                el('a').addClass('feed-result-title').attr({
                    href: feed.url,
                    target: '_blank',
                    rel: 'noopener'
                }).text(feed.title || feed.url).appendTo($head);
                $main.append($head);
                el('div').addClass('feed-result-url').text(feed.url).appendTo($main);
                $item.append($main);

                var $actions = el('div').addClass('feed-result-actions');
                el('button').attr('type', 'button')
                    .addClass('rss-action rss-action-outline feed-preview-trigger')
                    .text('Preview')
                    .data('feed', feed)
                    .appendTo($actions);
                el('a').addClass('rss-action rss-action-primary').attr({
                    href: feed.url,
                    target: '_blank',
                    rel: 'noopener'
                }).text('Open').appendTo($actions);
                el('button').attr('type', 'button')
                    .addClass('rss-action rss-action-muted feed-copy-trigger')
                    .text('Copy')
                    .data('url', feed.url)
                    .appendTo($actions);
                $item.append($actions);
                $results.append($item);
            });
        }

        function captchaValue() {
            return $('input[name="cap-token"]').val() || '';
        }

        function resetCaptcha() {
            var widget = document.querySelector('cap-widget');
            if (widget && typeof widget.reset === 'function') {
                widget.reset();
                if (typeof widget.solve === 'function') {
                    widget.solve();
                }
            }
        }

        function focusCaptcha() {
            var widget = document.querySelector('cap-widget');
            if (widget && widget.scrollIntoView) {
                widget.scrollIntoView({behavior: 'smooth', block: 'center'});
            }
        }

        function setStatus(message, loading) {
            $status.toggleClass('is-loading', Boolean(loading));
            if (loading) {
                $status.empty().append(
                    $('<span>', {'class': 'rss-spinner', 'aria-hidden': 'true'}),
                    document.createTextNode(' ' + message)
                );
            } else {
                $status.text(message);
            }
        }

        function showSkeletons() {
            $results.empty();
            for (var i = 0; i < 3; i++) {
                $results.append(
                    '<li class="feed-result feed-result-skeleton" aria-hidden="true">' +
                    '<span class="skeleton-favicon"></span>' +
                    '<span class="skeleton-lines">' +
                    '<span class="skeleton-line"></span>' +
                    '<span class="skeleton-line short"></span>' +
                    '</span></li>');
            }
        }

        function runDiscovery(url, scrollToResults) {
            url = normalizeUrl(url);
            if (!url) {
                setStatus('Enter a page URL first.');
                return;
            }
            if (running) {
                return;
            }
            var captcha = captchaValue();
            if (!captcha) {
                setStatus('Complete the verification first.');
                focusCaptcha();
                return;
            }

            running = true;
            $submit.prop('disabled', true);
            setStatus('Looking for feeds…', true);
            showSkeletons();
            $results.attr('aria-busy', 'true');

            $.ajax({
                url: '/discover',
                method: 'POST',
                data: {
                    url: url,
                    captcha: captcha,
                    csrfmiddlewaretoken: $('input[name="csrfmiddlewaretoken"]').val()
                },
                dataType: 'json'
            }).done(function (data) {
                var feeds = (data && data.feeds) || [];
                if (!feeds.length) {
                    setStatus('No RSS feed found — opening the feed builder…');
                    openFeedBuilder(url);
                    return;
                }
                renderResults(feeds, url);
                if (window.history && window.history.replaceState) {
                    window.history.replaceState(null, '', '?q=' + encodeURIComponent(url));
                }
                if (scrollToResults) {
                    var top = $('.rss-finder-hero').offset().top - 20;
                    $('html, body').animate({scrollTop: top}, 300);
                }
            }).fail(function (xhr) {
                var message = 'Feed discovery failed.';
                var captchaFailed = false;
                try {
                    var parsed = JSON.parse(xhr.responseText);
                    message = parsed.error || message;
                    captchaFailed = Boolean(parsed.captcha);
                } catch (ignore) {
                    // keep the generic message
                }
                if (xhr.status === 400) {
                    setStatus(message);
                    if (captchaFailed) {
                        focusCaptcha();
                    }
                    return;
                }
                setStatus(message + ' Opening the feed builder…');
                openFeedBuilder(url);
            }).always(function () {
                running = false;
                $submit.prop('disabled', false);
                $results.find('.feed-result-skeleton').remove();
                $results.attr('aria-busy', 'false');
                resetCaptcha();
            });
        }

        $form.on('submit', function (event) {
            event.preventDefault();
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
            setStatus('Complete the verification, then press Find RSS.');
            focusCaptcha();
        }
    });
})(jQuery);
