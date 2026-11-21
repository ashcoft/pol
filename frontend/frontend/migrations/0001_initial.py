# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='Feed',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('uri', models.CharField(max_length=2000)),
                ('xpath', models.CharField(max_length=2000)),
            ],
        ),
        migrations.CreateModel(
            name='FeedField',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('xpath', models.CharField(max_length=2000)),
                ('feed', models.ForeignKey(to='frontend.Feed', on_delete=django.db.models.deletion.CASCADE)),
            ],
        ),
        migrations.CreateModel(
            name='Field',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('name', models.CharField(max_length=200)),
            ],
        ),
        migrations.AddField(
            model_name='feedfield',
            name='field',
            field=models.ForeignKey(to='frontend.Field', on_delete=django.db.models.deletion.CASCADE),
        ),
    ]
