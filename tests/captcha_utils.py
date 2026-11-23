"""Helpers for tests that must pass the Cap gate."""


def captcha_data():
    """Return the token accepted by CAP_TEST_MODE."""
    return {'cap-token': 'passed'}
