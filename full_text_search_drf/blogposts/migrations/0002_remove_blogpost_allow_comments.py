# -*- coding: utf-8 -*-
# Generated by Django 1.9.1 on 2016-01-10 16:38
from __future__ import unicode_literals

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('blogposts', '0001_initial'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='blogpost',
            name='allow_comments',
        ),
    ]