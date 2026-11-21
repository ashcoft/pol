from django.db import migrations


def add_fields(apps, schema_editor):
    Field = apps.get_model('frontend', 'Field')
    # Use the fixture's primary keys so loading fields.json later updates these
    # rows instead of colliding with them.
    Field.objects.get_or_create(name='date', defaults={'required': False, 'pk': 4})
    Field.objects.get_or_create(name='image', defaults={'required': False, 'pk': 5})


def keep_fields(apps, schema_editor):
    """Reverse is a no-op: deleting the rows would cascade to saved FeedField
    selectors and silently break existing feeds."""


class Migration(migrations.Migration):

    dependencies = [
        ('frontend', '0009_post_md5sum_index'),
    ]

    operations = [
        migrations.RunPython(add_fields, keep_fields),
    ]
