# Generated by Django 3.1.8 on 2021-06-23 00:45

import datetime
import django.core.validators
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('marketplace', '0026_auto_20210616_1544'),
    ]

    operations = [
        migrations.AlterField(
            model_name='item',
            name='deadline',
            field=models.DateField(help_text='Latest allowed is 2022-06-23', validators=[django.core.validators.MinValueValidator(datetime.date(2021, 6, 23)), django.core.validators.MaxValueValidator(datetime.date(2022, 6, 23))]),
        ),
        migrations.AlterField(
            model_name='item',
            name='description',
            field=models.CharField(max_length=1000),
        ),
        migrations.AlterField(
            model_name='itemrequest',
            name='deadline',
            field=models.DateField(help_text='Latest allowed is 2022-06-23', validators=[django.core.validators.MinValueValidator(datetime.date(2021, 6, 23)), django.core.validators.MaxValueValidator(datetime.date(2022, 6, 23))]),
        ),
        migrations.AlterField(
            model_name='itemrequest',
            name='description',
            field=models.CharField(max_length=1000),
        ),
        migrations.AlterField(
            model_name='message',
            name='text',
            field=models.CharField(max_length=2000),
        ),
    ]
