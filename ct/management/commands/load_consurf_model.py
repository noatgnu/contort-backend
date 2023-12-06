import os

from django.core.files import File
from django.core.management import BaseCommand
from django.db import transaction

from ct.models import CONSURFModel


class Command(BaseCommand):
    """
    A command that remove all rows from sample model table and load data from provided txt files
    """
    def add_arguments(self, parser):
        parser.add_argument('folder_path', type=str, help='Path to the folder containing consurf data')
    def handle(self, *args, **options):
        folder_path = options['folder_path']
        with transaction.atomic():
            # walk through the folder and detect subfolders, get subfolder name as uniprot_accession.
            # check if uniprot_accession already exists in the CONSURFModel table. If exists, skip.
            # get consurf_grade.txt in each subfolder as consurf_grade
            # get msa_aa_variety_percentage.csv in each subfolder as consurf_msa_variation
            # create a CONSURFModel object for each subfolder
            for root, dirs, files in os.walk(folder_path):
                for dir in dirs:
                    consurf_grade = os.path.join(root, dir, "consurf_grades.txt")
                    consurf_msa_variation = os.path.join(root, dir, "msa_aa_variety_percentage.csv")
                    if os.path.isfile(consurf_grade) is False or os.path.isfile(consurf_msa_variation) is False:
                        continue
                    if CONSURFModel.objects.filter(uniprot_accession=dir).exists():
                        continue

                    consurf = CONSURFModel.objects.create(uniprot_accession=dir)
                    consurf.consurf_grade.save("consurf_grades.txt", File(open(consurf_grade, "rb")))
                    consurf.consurf_msa_variation.save("msa_aa_variety_percentage.csv",
                                                       File(open(consurf_msa_variation, "rb")))
                    consurf.save()
