# Generated by Django 3.1.8 on 2021-08-14 06:06

import datetime
import django.core.validators
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('marketplace', '0031_auto_20210812_1844'),
    ]

    operations = [
        migrations.AddField(
            model_name='itemflag',
            name='reporter',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, related_name='item_flags', to='marketplace.account'),
        ),
        migrations.AddField(
            model_name='itemrequestflag',
            name='reporter',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, related_name='item_request_flags', to='marketplace.account'),
        ),
        migrations.AlterField(
            model_name='item',
            name='deadline',
            field=models.DateField(help_text='Latest allowed is 2022-08-14', validators=[django.core.validators.MinValueValidator(datetime.date(2021, 8, 14)), django.core.validators.MaxValueValidator(datetime.date(2022, 8, 14))]),
        ),
        migrations.AlterField(
            model_name='itemrequest',
            name='deadline',
            field=models.DateField(help_text='Latest allowed is 2022-08-14', validators=[django.core.validators.MinValueValidator(datetime.date(2021, 8, 14)), django.core.validators.MaxValueValidator(datetime.date(2022, 8, 14))]),
        ),
    ]
