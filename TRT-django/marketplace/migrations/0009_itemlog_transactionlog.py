# Generated by Django 3.1.7 on 2021-03-24 17:14

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('marketplace', '0008_auto_20210320_2341'),
    ]

    operations = [
        migrations.CreateModel(
            name='TransactionLog',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('datetime', models.DateTimeField()),
                ('log', models.CharField(max_length=100)),
                ('account', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='transaction_logs', to='marketplace.account')),
                ('transaction', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='logs', to='marketplace.transaction')),
            ],
        ),
        migrations.CreateModel(
            name='ItemLog',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('datetime', models.DateTimeField()),
                ('log', models.CharField(max_length=100)),
                ('account', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='item_logs', to='marketplace.account')),
                ('item', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='logs', to='marketplace.item')),
            ],
        ),
    ]