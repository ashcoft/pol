from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('frontend', '0008_auto_20180215_1445'),
    ]

    operations = [
        # 0008 already creates md5sum_index with raw SQL. Record it in the
        # migration state so makemigrations does not add a duplicate index.
        migrations.SeparateDatabaseAndState(
            state_operations=[
                migrations.AddIndex(
                    model_name='post',
                    index=models.Index(fields=['feed', 'md5sum'], name='md5sum_index'),
                ),
            ],
        ),
    ]
