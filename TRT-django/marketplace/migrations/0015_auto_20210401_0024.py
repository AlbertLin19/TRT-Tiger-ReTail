# Generated by Django 3.1.7 on 2021-04-01 04:24

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('marketplace', '0014_request'),
    ]

    operations = [
        migrations.RenameModel(
            old_name='Request',
            new_name='ItemRequest',
        ),
    ]
