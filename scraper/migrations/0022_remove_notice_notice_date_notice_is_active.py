# Generated by Django 5.1 on 2024-12-10 13:04

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('scraper', '0021_notice'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='notice',
            name='notice_date',
        ),
        migrations.AddField(
            model_name='notice',
            name='is_active',
            field=models.BooleanField(default=True),
        ),
    ]
