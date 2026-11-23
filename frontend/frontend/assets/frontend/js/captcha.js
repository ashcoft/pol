(function ($) {
    'use strict';

    $(function () {
        $('.captcha-refresh').on('click', function (event) {
            event.preventDefault();
            var $button = $(this);
            var $form = $button.closest('form');
            if (!$form.length) {
                $form = $(document);
            }
            var url = $button.data('captcha-refresh-url') || '/captcha/refresh/';

            $.getJSON(url, function (data) {
                $form.find('img.captcha').attr('src', data.image_url);
                $form.find('input[name="captcha_0"]').val(data.key);
                $form.find('input[name="captcha_1"]').val('').trigger('focus');
            });
        });
    });
})(jQuery);
