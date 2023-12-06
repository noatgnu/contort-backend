# Generated by Django 5.0 on 2023-12-05 19:52

from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='CONSURFModel',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('uniprot_accession', models.CharField(blank=True, max_length=20, null=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('consurf_grade', models.FileField(blank=True, null=True, upload_to='consurf_grade')),
                ('consurf_msa_variantion', models.FileField(blank=True, null=True, upload_to='consurf_msa_variantion')),
            ],
            options={
                'ordering': ['id'],
            },
        ),
    ]
