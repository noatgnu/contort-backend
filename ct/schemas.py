from typing import Type, Dict

from ninja import Schema, UploadedFile
from ninja_jwt.schema import TokenObtainPairInputSchema, TokenObtainInputSchemaBase
from ninja_jwt.tokens import RefreshToken


class CONSURFModelSchema(Schema):
    uniprot_accession: str
    consurf_grade: str
    consurf_msa_variation: str


class UploadCONSURFSchema(Schema):
    uniprot_accession: str
    consurf_grade: UploadedFile
    consurf_msa_variation: UploadedFile


class CONSURFGrade(Schema):
    POS: int
    SEQ: str
    SCORE: float
    COLOR: str
    CONFIDENCE_INTERVAL: list[float]
    CONFIDENCE_INTERVAL_COLORS: list[str]
    MSA_DATA: list[int]
    RESIDUE_VARIETY: list[str]
    BE: str
    FUNCTION: str

class CONSURFMSAVar(Schema):
    pos: int
    A: float
    C: float
    D: float
    E: float
    F: float
    G: float
    H: float
    I: float
    K: float
    L: float
    M: float
    N: float
    P: float
    Q: float
    R: float
    S: float
    T: float
    V: float
    W: float
    Y: float
    OTHER: float
    MAX_AA: str
    ConSurf_Grade: str

class ConsurfJobSchema(Schema):
    job_title: str
    query_sequence: str
    alignment_program: str
    fasta_database_id: int

class ProteinFastaDatabaseSchema(Schema):
    name: str
    fasta_file: UploadedFile

class UserSchema(Schema):
    first_name: str
    email: str


class MyTokenObtainPairOutSchema(Schema):
    refresh: str
    access: str
    user: UserSchema


class MyTokenObtainPairInputSchema(TokenObtainInputSchemaBase):
    @classmethod
    def get_response_schema(cls) -> Type[Schema]:
        return MyTokenObtainPairOutSchema

    @classmethod
    def get_token(cls, user) -> Dict:
        values = {}
        refresh = RefreshToken.for_user(user)
        values["refresh"] = str(refresh)
        values["access"] = str(refresh.access_token)
        values.update(user=UserSchema.from_orm(user)) # this will be needed when creating output schema
        return values