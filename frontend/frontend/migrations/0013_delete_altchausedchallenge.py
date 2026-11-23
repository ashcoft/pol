from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('frontend', '0012_altcha_used_challenge'),
    ]

    operations = [
        migrations.DeleteModel(name='AltchaUsedChallenge'),
    ]
