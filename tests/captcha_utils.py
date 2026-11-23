"""Helpers for tests that must pass the Altcha gate."""


def captcha_data():
    """Create and solve an Altcha challenge for a form submission."""
    import datetime

    import altcha
    from django.conf import settings

    challenge = altcha.create_challenge(
        algorithm='PBKDF2/SHA-256',
        cost=10,
        expires_at=datetime.datetime.now(datetime.timezone.utc)
        + datetime.timedelta(minutes=5),
        hmac_secret=settings.ALTCHA_HMAC_KEY,
    )
    solution = altcha.solve_challenge(challenge, timeout=10)
    return {'captcha': altcha.Payload(challenge, solution).to_base64()}
