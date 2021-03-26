# Generated by Django 3.1.7 on 2021-03-26 17:07

import datetime
import django.core.validators
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('marketplace', '0009_itemlog_transactionlog'),
    ]

    operations = [
        migrations.AlterField(
            model_name='item',
            name='condition',
            field=models.DecimalField(choices=[(0, 'New'), (1, 'Like new'), (2, 'Gently-loved'), (3, 'Well-loved'), (4, 'Poor')], decimal_places=0, max_digits=1),
        ),
        migrations.AlterField(
            model_name='item',
            name='deadline',
            field=models.DateField(help_text='Latest allowed is 2022-03-26', validators=[django.core.validators.MinValueValidator(datetime.date(2021, 3, 26)), django.core.validators.MaxValueValidator(datetime.date(2022, 3, 26))], verbose_name='Deadline to Sell'),
        ),
        migrations.AlterField(
            model_name='item',
            name='name',
            field=models.CharField(max_length=50, verbose_name='Item Name'),
        ),
    ]
