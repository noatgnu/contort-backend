# Generated by Django 5.1.4 on 2025-01-12 15:58

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('ct', '0011_remove_consurfjob_email_notification_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='consurfjob',
            name='email_notification',
            field=models.BooleanField(default=False),
        ),
    ]
