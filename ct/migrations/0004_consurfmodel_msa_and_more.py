# Generated by Django 5.0 on 2023-12-19 14:53

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('ct', '0003_alter_consurfmodel_uniprot_accession'),
    ]

    operations = [
        migrations.AddField(
            model_name='consurfmodel',
            name='msa',
            field=models.FileField(blank=True, null=True, upload_to='msa'),
        ),
        migrations.AlterField(
            model_name='consurfmodel',
            name='consurf_msa_variation',
            field=models.FileField(blank=True, null=True, upload_to='consurf_msa_variation'),
        ),
    ]
