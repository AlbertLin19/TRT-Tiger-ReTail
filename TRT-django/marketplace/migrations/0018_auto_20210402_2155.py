# Generated by Django 3.1.7 on 2021-04-03 01:55

import datetime
import django.core.validators
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('marketplace', '0017_itemrequestlog'),
    ]

    operations = [
        migrations.AddField(
            model_name='account',
            name='contacts',
            field=models.ManyToManyField(related_name='_account_contacts_+', to='marketplace.Account'),
        ),
        migrations.AlterField(
            model_name='item',
            name='deadline',
            field=models.DateField(help_text='Latest allowed is 2022-04-03', validators=[django.core.validators.MinValueValidator(datetime.date(2021, 4, 3)), django.core.validators.MaxValueValidator(datetime.date(2022, 4, 3))]),
        ),
        migrations.AlterField(
            model_name='itemrequest',
            name='deadline',
            field=models.DateField(help_text='Latest allowed is 2022-04-03', validators=[django.core.validators.MinValueValidator(datetime.date(2021, 4, 3)), django.core.validators.MaxValueValidator(datetime.date(2022, 4, 3))]),
        ),
        migrations.CreateModel(
            name='Message',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('text', models.TextField()),
                ('receiver', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='received_messages', to='marketplace.account')),
                ('sender', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='sent_messages', to='marketplace.account')),
            ],
        ),
    ]