(function ($) {
    'use strict';

    $(function () {
        var $button = $('#find-feeds-btn');
        if (!$button.length) {
            return;
        }

        var $status = $('#feed-finder-status');
        var $results = $('#feed-finder-results');

        $button.on('click', function () {
            var url = $.trim($('input[name="url"]').val() || '');
            if (!url) {
                $status.text('Enter a page URL first.');
                return;
            }

            $button.prop('disabled', true);
            $status.text('Looking for feeds…');
            $results.empty();

            $.ajax({url: '/discover', data: {url: url}, dataType: 'json'})
                .done(function (data) {
                    var feeds = (data && data.feeds) || [];
                    if (!feeds.length) {
                        $status.text('No feeds found on this page.');
                        return;
                    }
                    $status.text(feeds.length + ' feed(s) found:');
                    $.each(feeds, function (_index, feed) {
                        var $item = $('<li>');
                        $('<a>').attr('href', feed.url)
                            .text(feed.title || feed.url).appendTo($item);
                        if (feed.type) {
                            $('<span>').addClass('muted').text(' ' + feed.type).appendTo($item);
                        }
                        $('<a>').addClass('btn btn-mini')
                            .attr('href', '/read?url=' + encodeURIComponent(feed.url) + '&format=html')
                            .text('Preview').appendTo($item);
                        $item.appendTo($results);
                    });
                })
                .fail(function (xhr) {
                    var message = 'Feed discovery failed.';
                    try {
                        message = JSON.parse(xhr.responseText).error || message;
                    } catch (ignore) {
                        // keep the generic message
                    }
                    $status.text(message);
                })
                .always(function () {
                    $button.prop('disabled', false);
                });
        });
    });
})(jQuery);
