from django.db import models


# Create your models here.
class CONSURFModel(models.Model):
    """A data model for storing protein conservation data with the following column:
    - uniprot_accession: the UniProt accession number of the protein
    - consurf_grade: the conservation grade of the protein
    """
    uniprot_accession = models.CharField(max_length=20, blank=True, null=True, unique=True, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    consurf_grade = models.FileField(upload_to="consurf_grade", blank=True, null=True)
    consurf_msa_variation = models.FileField(upload_to="consurf_msa_variantion", blank=True, null=True)

    class Meta:
        ordering = ["id"]
        app_label = "ct"

    def __str__(self):
        return f"{self.uniprot_accession}"

    def delete(self, using=None, keep_parents=False):
        self.consurf_grade.delete()
        self.consurf_msa_variation.delete()
        super().delete(using=using, keep_parents=keep_parents)

