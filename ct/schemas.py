from ninja import Schema, UploadedFile


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