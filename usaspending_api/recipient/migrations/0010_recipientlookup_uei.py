# Generated by Django 2.2.17 on 2021-10-05 20:05

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('recipient', '0009_recipientprofile_uei'),
    ]

    operations = [
        migrations.AddField(
            model_name='recipientlookup',
            name='uei',
            field=models.TextField(null=True),
        ),
    ]