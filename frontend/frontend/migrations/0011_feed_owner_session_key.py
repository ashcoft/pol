from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('frontend', '0010_date_image_fields'),
    ]

    operations = [
        migrations.AddField(
            model_name='feed',
            name='owner',
            field=models.ForeignKey(
                blank=True, null=True, on_delete=django.db.models.deletion.CASCADE,
                related_name='feeds', to=settings.AUTH_USER_MODEL),
        ),
        migrations.AddField(
            model_name='feed',
            name='session_key',
            field=models.CharField(
                blank=True, default='', db_index=True, max_length=40),
        ),
    ]
