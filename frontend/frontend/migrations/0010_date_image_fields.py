from django.db import migrations


def add_fields(apps, schema_editor):
    Field = apps.get_model('frontend', 'Field')
    Field.objects.get_or_create(name='date', defaults={'required': False})
    Field.objects.get_or_create(name='image', defaults={'required': False})


def remove_fields(apps, schema_editor):
    Field = apps.get_model('frontend', 'Field')
    Field.objects.filter(name__in=['date', 'image']).delete()


class Migration(migrations.Migration):

    dependencies = [
        ('frontend', '0009_post_md5sum_index'),
    ]

    operations = [
        # Fixtures are not replayed on existing deployments.
        migrations.RunPython(add_fields, remove_fields),
    ]
