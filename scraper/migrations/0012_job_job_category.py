# Generated by Django 5.1 on 2024-09-13 09:09

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('scraper', '0011_job_created_at'),
    ]

    operations = [
        migrations.AddField(
            model_name='job',
            name='job_category',
            field=models.CharField(blank=True, max_length=255, null=True),
        ),
    ]