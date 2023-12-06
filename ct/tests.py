from django.core.files.base import ContentFile
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, Client
from ninja.testing import TestClient
from django.test.client import MULTIPART_CONTENT, encode_multipart, BOUNDARY
from django.utils.datastructures import MultiValueDict


# Create your tests here.
class CONSURFModelTestCase(TestCase):
    def setUp(self):
        self.client = Client()

    def test_consurf_model_upload(self):
        with open(r'D:\PycharmProjects\coral-docker\data\lrrk2output\consurf_grades.txt', 'rb') as f, open(
                r'D:\PycharmProjects\coral-docker\data\lrrk2output\msa_aa_variety_percentage.csv', 'rb') as g:

            d = self.client.post('/api/consurf', {"uniprot_accession": "Q5S007", "consurf_grade": f, "consurf_msa_variation": g}, content_type=MULTIPART_CONTENT)
            print(d.content)
            assert d.status_code == 200
