from ninja import NinjaAPI, Form, Swagger

from ct import utils
from ct.models import CONSURFModel
from ct.schemas import CONSURFModelSchema, CONSURFGrade, CONSURFMSAVar
from ninja.files import UploadedFile
# Create your views here.

api = NinjaAPI(docs=Swagger())

@api.get("/consurf/{uniprot_accession}", response=CONSURFModelSchema)
def consurf(request, uniprot_accession: str):
    consurf = CONSURFModel.objects.get(uniprot_accession=uniprot_accession)
    return consurf

@api.post("/consurf", response=CONSURFModelSchema)
def create_consurf(request, uniprot_accession: Form[str], consurf_grade: UploadedFile, consurf_msa_variation: UploadedFile):
    consurf = CONSURFModel.objects.create(uniprot_accession=uniprot_accession, consurf_grade=consurf_grade, consurf_msa_variation=consurf_msa_variation)
    return consurf

@api.get("/consurf/{uniprot_accession}/consurf_grade", response=list[CONSURFGrade])
def consurf_grade(request, uniprot_accession: str):
    consurf = CONSURFModel.objects.get(uniprot_accession=uniprot_accession)
    df = utils.read_consurf_grade_file(consurf.consurf_grade.path)
    df.fillna("", inplace=True)
    return df.to_dict(orient="records")

@api.get("/consurf/{uniprot_accession}/consurf_msa_variation", response=list[CONSURFMSAVar])
def consurf_msa_variation(request, uniprot_accession: str):
    consurf = CONSURFModel.objects.get(uniprot_accession=uniprot_accession)
    df = utils.read_consurf_msa_variation_file(consurf.consurf_msa_variation.path)
    df.fillna("", inplace=True)
    return df.to_dict(orient="records")