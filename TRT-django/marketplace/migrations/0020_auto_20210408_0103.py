# Generated by Django 3.1.7 on 2021-04-08 05:03

import datetime
import django.core.validators
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('marketplace', '0019_message_datetime'),
    ]

    operations = [
        migrations.AlterField(
            model_name='item',
            name='deadline',
            field=models.DateField(help_text='Latest allowed is 2022-04-08', validators=[django.core.validators.MinValueValidator(datetime.date(2021, 4, 8)), django.core.validators.MaxValueValidator(datetime.date(2022, 4, 8))]),
        ),
        migrations.AlterField(
            model_name='itemrequest',
            name='deadline',
            field=models.DateField(help_text='Latest allowed is 2022-04-08', validators=[django.core.validators.MinValueValidator(datetime.date(2021, 4, 8)), django.core.validators.MaxValueValidator(datetime.date(2022, 4, 8))]),
        ),
        migrations.CreateModel(
            name='Notification',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('datetime', models.DateTimeField()),
                ('text', models.CharField(max_length=100)),
                ('seen', models.BooleanField(default=False)),
                ('account', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='notifications', to='marketplace.account')),
            ],
        ),
    ]
