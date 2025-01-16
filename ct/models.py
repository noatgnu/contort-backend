from django.conf import settings
from django.db import models
from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver
from rest_framework.authtoken.models import Token

class CONSURFModel(models.Model):
    """A data model for storing protein conservation data with the following column:
    - uniprot_accession: the UniProt accession number of the protein
    - consurf_grade: the conservation grade of the protein
    """
    uniprot_accession = models.CharField(max_length=20, blank=True, null=True, unique=True, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    consurf_grade = models.FileField(upload_to="consurf_grade", blank=True, null=True)
    consurf_msa_variation = models.FileField(upload_to="consurf_msa_variation", blank=True, null=True)
    msa = models.FileField(upload_to="msa", blank=True, null=True)
    consurf_job = models.ForeignKey("ConsurfJob", on_delete=models.SET_NULL, blank=True, null=True)
    user = models.ForeignKey(User, on_delete=models.SET_NULL, blank=True, null=True)

    class Meta:
        ordering = ["id"]
        app_label = "ct"

    def __str__(self):
        return f"{self.uniprot_accession}"

    def delete(self, using=None, keep_parents=False):
        self.consurf_grade.delete()
        self.consurf_msa_variation.delete()
        super().delete(using=using, keep_parents=keep_parents)

class ProteinFastaDatabase(models.Model):
    name = models.CharField(max_length=255)
    fasta_file = models.FileField(upload_to="fasta_files")
    uploaded_at = models.DateTimeField(auto_now_add=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE)

class MultipleSequenceAlignment(models.Model):
    name = models.CharField(max_length=255)
    msa_file = models.FileField(upload_to="msa_files")
    uploaded_at = models.DateTimeField(auto_now_add=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE)

class StructureFile(models.Model):
    name = models.CharField(max_length=255)
    structure_file = models.FileField(upload_to="structure_files")
    uploaded_at = models.DateTimeField(auto_now_add=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    chains = models.TextField(blank=True, null=True)

class ConsurfJob(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    job_title = models.CharField(max_length=255)
    query_sequence = models.TextField(blank=True, null=True)
    alignment_program = models.CharField(max_length=255, blank=True, null=True)
    fasta_database = models.ForeignKey(ProteinFastaDatabase, on_delete=models.CASCADE, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=50, default='pending')
    updated_at = models.DateTimeField(auto_now=True)
    log_data = models.TextField(blank=True, null=True)
    error_data = models.TextField(blank=True, null=True)
    process_cmd = models.TextField(blank=True, null=True)
    max_homologs = models.IntegerField(default=150)
    max_iterations = models.IntegerField(default=1)
    substitution_model = models.CharField(max_length=255, default='BEST')
    maximum_likelihood = models.BooleanField(default=False)
    max_id = models.IntegerField(default=95)
    min_id = models.IntegerField(default=35)
    closest = models.BooleanField(default=False)
    cutoff = models.FloatField(default=0.0001)
    algorithm = models.CharField(max_length=255, default='HMMER')
    email_notification = models.BooleanField(default=False)
    msa = models.ForeignKey(MultipleSequenceAlignment, on_delete=models.SET_NULL, null=True, blank=True)
    uniprot_accession = models.CharField(max_length=20, blank=True, null=True)
    chain = models.CharField(max_length=1, blank=True, null=True)
    structure_file = models.ForeignKey(StructureFile, on_delete=models.SET_NULL, null=True, blank=True)
    query_name = models.CharField(max_length=255, blank=True, null=True)
    session_id = models.CharField(max_length=255, blank=True, null=True)

    class Meta:
        ordering = ["-id"]
        app_label = "ct"

@receiver(post_save, sender=settings.AUTH_USER_MODEL)
def create_auth_token(sender, instance=None, created=False, **kwargs):
    if created:
        Token.objects.create(user=instance)