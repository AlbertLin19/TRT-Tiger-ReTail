# Generated by Django 3.1.7 on 2021-03-13 19:45

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('marketplace', '0004_auto_20210313_1345'),
    ]

    operations = [
        migrations.AddField(
            model_name='account',
            name='username',
            field=models.CharField(default='', max_length=50, unique=True),
            preserve_default=False,
        ),
    ]
