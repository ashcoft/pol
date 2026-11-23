from django.conf import settings
from django.db import models

class Feed(models.Model):
    uri = models.CharField(max_length=2000)
    xpath = models.CharField(max_length=2000)
    edited = models.BooleanField(default=False)
    created = models.DateTimeField(auto_now_add=True)
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True,
        on_delete=models.CASCADE, related_name='feeds')
    # Anonymous feeds belong to the browser session that created them. The key
    # is cleared when the feed is claimed by a signed-in user.
    session_key = models.CharField(max_length=40, blank=True, default='', db_index=True)

class Field(models.Model):
    name = models.CharField(max_length=200)
    required = models.BooleanField(default=True)

class FeedField(models.Model):
    feed = models.ForeignKey(Feed, on_delete=models.CASCADE)
    field = models.ForeignKey(Field, on_delete=models.CASCADE)
    xpath = models.CharField(max_length=2000)

class Post(models.Model):
    feed = models.ForeignKey(Feed, on_delete=models.CASCADE)
    md5sum = models.BinaryField(max_length=16)
    created = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [models.Index(fields=['feed', 'md5sum'], name='md5sum_index')]


class AltchaUsedChallenge(models.Model):
    """Signed Altcha challenges that have already been solved.

    The unique signature makes replay protection work across all Gunicorn
    workers without relying on a shared cache.
    """
    signature = models.CharField(max_length=128, unique=True)
    expires_at = models.DateTimeField(db_index=True)
    created = models.DateTimeField(auto_now_add=True)
