from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('frontend', '0011_feed_owner_session_key'),
    ]

    operations = [
        migrations.CreateModel(
            name='AltchaUsedChallenge',
            fields=[
                ('id', models.AutoField(
                    auto_created=True, primary_key=True, serialize=False,
                    verbose_name='ID')),
                ('signature', models.CharField(max_length=128, unique=True)),
                ('expires_at', models.DateTimeField(db_index=True)),
                ('created', models.DateTimeField(auto_now_add=True)),
            ],
        ),
    ]
