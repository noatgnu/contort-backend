# Generated by Django 5.0 on 2023-12-05 21:17

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('ct', '0001_initial'),
    ]

    operations = [
        migrations.RenameField(
            model_name='consurfmodel',
            old_name='consurf_msa_variantion',
            new_name='consurf_msa_variation',
        ),
    ]
