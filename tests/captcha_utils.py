"""Helpers for tests that must pass the captcha gate."""


def captcha_data():
    """Create a fresh captcha and return the fields a form must submit."""
    from captcha.models import CaptchaStore

    key = CaptchaStore.generate_key()
    response = CaptchaStore.objects.get(hashkey=key).response
    return {'captcha_0': key, 'captcha_1': response}
