# -*- coding: utf-8 -*-
# Generated by Django 1.10.1 on 2016-10-13 18:23
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('awards', '0033_auto_20161011_1545'),
    ]

    operations = [
        migrations.AlterField(
            model_name='award',
            name='description',
            field=models.CharField(max_length=4000, null=True),
        ),
        migrations.AlterField(
            model_name='financialassistanceaward',
            name='award_description',
            field=models.CharField(max_length=4000, null=True),
        ),
        migrations.AlterField(
            model_name='procurement',
            name='award_description',
            field=models.CharField(max_length=4000, null=True),
        ),
        migrations.AlterField(
            model_name='procurement',
            name='referenced_idv_modification_number',
            field=models.CharField(blank=True, max_length=25, null=True),
        ),
    ]
