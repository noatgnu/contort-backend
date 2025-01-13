import io
import json
import os

import requests
from django.conf import settings
from django.contrib.auth.models import User
from django.core.files.base import File
from django.core.signing import TimestampSigner, BadSignature
from django.http import HttpResponse
from django_sendfile import sendfile
from drf_chunked_upload.exceptions import ChunkedUploadError
from drf_chunked_upload.models import ChunkedUpload
from drf_chunked_upload.views import ChunkedUploadView
from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.generics import get_object_or_404
from rest_framework.parsers import MultiPartParser, JSONParser
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from ct import utils
from ct.models import CONSURFModel, ConsurfJob, ProteinFastaDatabase, MultipleSequenceAlignment, StructureFile
from ct.serializers import CONSURFModelSerializer, ProteinFastaDatabaseSerializer, ConsurfJobSerializer, UserSerializer, \
    MultipleSequenceAlignmentSerializer, StructureFileSerializer
from ct.tasks import run_consurf_job


class DataChunkedUploadView(ChunkedUploadView):
    permission_classes = [permissions.IsAuthenticated]
    parser_classes = (MultiPartParser,)

    def _put_chunk(self, request, pk=None, whole=False, *args, **kwargs):
        try:
            chunk = request.data[self.field_name]
        except KeyError:
            raise ChunkedUploadError(status=status.HTTP_400_BAD_REQUEST,
                                     detail='No chunk file was submitted')

        if whole:
            start = 0
            total = chunk.size
            end = total - 1
        else:
            content_range = request.META.get('HTTP_CONTENT_RANGE', '')
            match = self.content_range_pattern.match(content_range)
            if not match:
                raise ChunkedUploadError(status=status.HTTP_400_BAD_REQUEST,
                                         detail='Error in request headers')

            start = int(match.group('start'))
            end = int(match.group('end'))
            total = int(match.group('total'))

        chunk_size = end - start + 1
        max_bytes = self.get_max_bytes(request)

        if end > total:
            raise ChunkedUploadError(
                status=status.HTTP_400_BAD_REQUEST,
                detail='End of chunk exceeds reported total (%s bytes)' % total
            )

        if max_bytes is not None and total > max_bytes:
            raise ChunkedUploadError(
                status=status.HTTP_400_BAD_REQUEST,
                detail='Size of file exceeds the limit (%s bytes)' % max_bytes
            )

        if chunk.size != chunk_size:
            raise ChunkedUploadError(
                status=status.HTTP_400_BAD_REQUEST,
                detail="File size doesn't match headers: file size is {} but {} reported".format(
                    chunk.size,
                    chunk_size,
                ),
            )

        if pk:
            upload_id = pk
            chunked_upload = get_object_or_404(self.get_queryset(),
                                               pk=upload_id)
            self.is_valid_chunked_upload(chunked_upload)
            if chunked_upload.offset != start:
                raise ChunkedUploadError(
                    status=status.HTTP_400_BAD_REQUEST,
                    detail='Offsets do not match',
                    expected_offset=chunked_upload.offset,
                    provided_offset=start,
                )

            chunked_upload.append_chunk(chunk, chunk_size=chunk_size)
        else:
            kwargs = {'offset': chunk.size}
            if hasattr(self.model, self.user_field_name):
                if hasattr(request, 'user') and request.user.is_authenticated:
                    kwargs[self.user_field_name] = request.user
                elif self.model._meta.get_field(self.user_field_name).null:
                    kwargs[self.user_field_name] = None
                else:
                    raise ChunkedUploadError(
                        status=status.HTTP_400_BAD_REQUEST,
                        detail="Upload requires user authentication but user cannot be determined",
                    )
            print(request.data)
            chunked_upload = self.serializer_class(data=request.data)
            if not chunked_upload.is_valid():
                raise ChunkedUploadError(status=status.HTTP_400_BAD_REQUEST,
                                         detail=chunked_upload.errors)

            # chunked_upload is currently a serializer;
            # save returns model instance
            chunked_upload = chunked_upload.save(**kwargs)

        return chunked_upload

    def on_completion(self, chunked_upload, request):
        return super().on_completion(chunked_upload, request)

class CONSURFModelViewSet(viewsets.ModelViewSet):
    queryset = CONSURFModel.objects.all()
    serializer_class = CONSURFModelSerializer
    permission_classes = [permissions.IsAuthenticated]

    @action(permission_classes=[AllowAny], detail=False, methods=['get'], url_path='consurf_grade/(?P<uniprot_accession>[^/.]+)')
    def consurf_grade(self, request, uniprot_accession=None):
        if uniprot_accession is None:
            return Response()
        consurf = CONSURFModel.objects.get(uniprot_accession=uniprot_accession)
        df = utils.read_consurf_grade_file(consurf.consurf_grade.path)
        df.fillna("", inplace=True)
        return Response(df.to_dict(orient="records"))

    @action(permission_classes=[AllowAny], detail=False, methods=['get'], url_path='consurf_msa_variation/(?P<uniprot_accession>[^/.]+)')
    def consurf_msa_variation(self, request, uniprot_accession=None):
        if uniprot_accession is None:
            return Response()
        consurf = CONSURFModel.objects.get(uniprot_accession=uniprot_accession)
        df = utils.read_consurf_msa_variation_file(consurf.consurf_msa_variation.path)
        df.fillna("", inplace=True)
        return Response(df.to_dict(orient="records"))

    @action(permission_classes=[AllowAny], detail=False, methods=['get'], url_path='files/msa/(?P<uniprot_accession>[^/.]+)')
    def consurf_msa_file(self, request, uniprot_accession=None):
        if uniprot_accession == "":
            return Response()
        consurf = CONSURFModel.objects.get(uniprot_accession=uniprot_accession)
        return sendfile(request, consurf.msa.path, mimetype="text/plain", attachment=True, attachment_filename=f"{consurf.uniprot_accession}_consurf_msa.txt")

    @action(permission_classes=[AllowAny], detail=False, methods=['get'])
    def count(self, request):
        return Response(CONSURFModel.objects.count())

    @action(permission_classes=[AllowAny], detail=False, methods=['get'], url_path='typeahead/(?P<uniprot_accession>[^/.]+)')
    def consurf_typeahead(self, request, uniprot_accession=None):
        if uniprot_accession == "":
            return Response([])
        consurf = CONSURFModel.objects.filter(uniprot_accession__startswith=uniprot_accession).order_by(
            "uniprot_accession")[:10]
        return Response([i.uniprot_accession for i in consurf])

class ProteinFastaDatabaseViewSet(viewsets.ModelViewSet):
    queryset = ProteinFastaDatabase.objects.all()
    serializer_class = ProteinFastaDatabaseSerializer
    permission_classes = [permissions.IsAuthenticated]
    parser_classes = (MultiPartParser, JSONParser)

    def get_queryset(self):
        user_id = self.request.user.id
        return ProteinFastaDatabase.objects.filter(user_id=user_id)

    def create(self, request, *args, **kwargs):
        upload_id = request.data.get("upload_id")
        name = request.data.get("name")
        cu = ChunkedUpload.objects.get(id=upload_id)
        file_path = cu.file.path
        fasta_database = ProteinFastaDatabase(name=name, user=request.user)
        with open(file_path, "rb") as f:
            fasta_database.fasta_file.save(cu.filename, f)
        fasta_database.user = request.user
        fasta_database.save()
        return Response(ProteinFastaDatabaseSerializer(fasta_database).data)

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        instance.fasta_file.delete()
        return super().destroy(request, *args, **kwargs)

class MultipleSequenceAlignmentViewSet(viewsets.ModelViewSet):
    queryset = MultipleSequenceAlignment.objects.all()
    serializer_class = MultipleSequenceAlignmentSerializer
    permission_classes = [permissions.IsAuthenticated]
    parser_classes = (MultiPartParser, JSONParser)

    def get_queryset(self):
        user_id = self.request.user.id
        return MultipleSequenceAlignment.objects.filter(user_id=user_id)

    def create(self, request, *args, **kwargs):
        upload_id = request.data.get("upload_id")
        name = request.data.get("name")
        cu = ChunkedUpload.objects.get(id=upload_id)
        file_path = cu.file.path
        msa = MultipleSequenceAlignment(name=name, user=request.user)
        with open(file_path, "rb") as f:
            msa.msa_file.save(cu.filename, f)

        msa.save()
        return Response(MultipleSequenceAlignmentSerializer(msa).data)

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        instance.msa_file.delete()
        return super().destroy(request, *args, **kwargs)

    @action(detail=True, methods=['get'], permission_classes=[permissions.IsAuthenticated])
    def get_all_sequence_names(self, request, pk=None):
        msa = self.get_object()
        path = msa.msa_file.path
        names = utils.get_all_sequence_names_from_alignment(path)
        return Response(names)

class StructureFileViewSet(viewsets.ModelViewSet):
    queryset = StructureFile.objects.all()
    serializer_class = StructureFileSerializer
    permission_classes = [permissions.IsAuthenticated]
    parser_classes = (MultiPartParser, JSONParser)

    def get_queryset(self):
        user_id = self.request.user.id
        return StructureFile.objects.filter(user_id=user_id)

    def create(self, request, *args, **kwargs):
        upload_id = request.data.get("upload_id")
        name = request.data.get("name")
        if "name" in request.data and "content" in request.data:
            structure = StructureFile(name=name, user=request.user)
            content: str = json.loads(request.data["content"])
            structure.structure_file.save(f"{name}.pdb", File(io.StringIO(content)))
            chains = utils.get_all_pdb_chains(structure.structure_file.path)
            structure.chains = ";".join(chains)
            structure.save()
        else:
            cu = ChunkedUpload.objects.get(id=upload_id)
            file_path = cu.file.path
            structure = StructureFile(name=name, user=request.user)
            with open(file_path, "rb") as f:
                structure.structure_file.save(cu.filename, f)
            chains = utils.get_all_pdb_chains(structure.structure_file.path)
            structure.chains = ";".join(chains)
            structure.save()
        return Response(StructureFileSerializer(structure).data)

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        instance.structure_file.delete()
        return super().destroy(request, *args, **kwargs)

class ConsurfJobViewSet(viewsets.ModelViewSet):
    queryset = ConsurfJob.objects.all()
    serializer_class = ConsurfJobSerializer
    permission_classes = [permissions.IsAuthenticated]
    parser_classes = (MultiPartParser, JSONParser)

    def get_queryset(self):
        user_id = self.request.user.id
        job_title = self.request.query_params.get("job_title")
        if job_title:
            return ConsurfJob.objects.filter(user_id=user_id, job_title__search=job_title)
        return ConsurfJob.objects.filter(user_id=user_id)

    def create(self, request, *args, **kwargs):
        data = request.data
        uniprot_id = data.get("uniprot_id", None)
        chain = data.get("chain", None)
        structure_id = data.get("structure_id", None)
        sequence = data.get("query_sequence")
        alignment_program = data.get("alignment_program", "MAFFT")
        fasta_database_id = data.get("fasta_database_id")
        model = data.get("model", "BEST")
        query_name = data.get("query_name", None)
        max_homologs = data.get("max_homologs", 150)
        if type(max_homologs) != int:
            max_homologs = int(max_homologs)
        cutoff = data.get("cutoff", 0.0001)
        if type(cutoff) != float:
            cutoff = float(cutoff)
        max_iterations = data.get("iterations", 1)
        if type(max_iterations) != int:
            max_iterations = int(max_iterations)
        max_id = data.get("max_id", 95)
        if type(max_id) != int:
            max_id = int(max_id)
        min_id = data.get("min_id", 35)
        if type(min_id) != int:
            min_id = int(min_id)
        closest = data.get("closest", False)
        if closest == "false":
            closest = False
        elif closest == "true":
            closest = True
        maximum_likelihood = data.get("maximum_likelihood", False)
        if maximum_likelihood == "false":
            maximum_likelihood = False
        elif maximum_likelihood == "true":
            maximum_likelihood = True
        algorithm = data.get("algorithm", "HMMER")
        job_title = data.get("job_title")
        msa_id = data.get("msa_id", None)


        consurf_job = ConsurfJob(
            user=request.user,
            query_sequence=sequence,
            alignment_program=alignment_program,
            max_homologs=max_homologs,
            max_iterations=max_iterations,
            substitution_model=model,
            max_id=max_id,
            min_id=min_id,
            closest=closest,
            cutoff=cutoff,
            algorithm=algorithm,
            maximum_likelihood=maximum_likelihood,
            job_title=job_title,
            uniprot_accession=uniprot_id
        )
        if fasta_database_id:
            fasta_database = ProteinFastaDatabase.objects.get(id=fasta_database_id, user=request.user)
            consurf_job.fasta_database = fasta_database
        if msa_id:
            msa = MultipleSequenceAlignment.objects.get(id=msa_id, user=request.user)
            consurf_job.msa = msa
            consurf_job.alignment_program = None
        if structure_id and chain:
            structure = StructureFile.objects.get(id=structure_id, user=request.user)
            consurf_job.structure_file = structure
            consurf_job.chain = chain
        if query_name:
            consurf_job.query_name = query_name
        consurf_job.save()
        run_consurf_job.delay(consurf_job.id)
        return Response(ConsurfJobSerializer(consurf_job).data)

    @action(detail=True, methods=['get'], permission_classes=[permissions.IsAuthenticated])
    def generate_download_token(self, request, pk=None):
        signer = TimestampSigner()
        token = signer.sign(pk)
        return Response({'token': token})

    @action(detail=False, methods=['get'], url_path='download', permission_classes=[permissions.AllowAny])
    def download_file(self, request):
        token = request.query_params.get('token')
        file_type = request.query_params.get('file_type')
        signer = TimestampSigner()
        try:
            job_id = signer.unsign(token, max_age=1800)  # 30 minutes
        except BadSignature:
            return Response({'error': 'Invalid or expired token'}, status=status.HTTP_400_BAD_REQUEST)
        job = get_object_or_404(ConsurfJob, pk=job_id)

        if file_type == 'zip':
            file_name = 'Consurf_Outputs.zip'
        elif file_type == 'msa_aa_variety_percentage':
            file_name = 'msa_aa_variety_percentage.csv'
        elif file_type == 'grades':
            file_name = 'no_model_consurf_grades.txt'
        else:
            return Response({'error': 'Invalid file type'}, status=status.HTTP_400_BAD_REQUEST)

        file_path = os.path.join(settings.MEDIA_ROOT, 'consurf_jobs', str(job_id), file_name)

        if not os.path.exists(file_path):
            return Response({'error': 'File not found'}, status=status.HTTP_404_NOT_FOUND)

        response = HttpResponse(status=200)
        response['Content-Type'] = 'application/octet-stream'
        response['Content-Disposition'] = f'attachment; filename={file_name}'
        response['X-Accel-Redirect'] = f'/media/consurf_jobs/{job_id}/{file_name}'
        return response

    @action(permission_classes=[AllowAny], detail=True, methods=['get'])
    def consurf_grade(self, request, pk=None):
        job = self.get_object()
        path = os.path.join(settings.MEDIA_ROOT, "consurf_jobs", str(job.id), "no_model_consurf_grades.txt")
        print(path)
        df = utils.read_consurf_grade_file_new(path)
        df.fillna("", inplace=True)
        return Response(df.to_dict(orient="records"))

    @action(permission_classes=[AllowAny], detail=True, methods=['get'])
    def consurf_msa_variation(self, request, pk=None):
        job = self.get_object()
        path = os.path.join(settings.MEDIA_ROOT, "consurf_jobs", str(job.id), "msa_aa_variety_percentage.csv")
        df = utils.read_consurf_msa_variation_file(path)
        df.fillna("", inplace=True)
        return Response(df.to_dict(orient="records"))

    @action(detail=False)
    def get_pdb(self, request):
        uniprot_id = request.query_params.get("uniprotID")
        url = f"https://alphafold.ebi.ac.uk/api/prediction/{uniprot_id}"
        response = requests.get(url)
        if response.status_code == 200:
            data = response.json()
            pdb_url = data[0].get("pdbUrl")
            res = requests.get(pdb_url)
            return Response(res.content)

class UserViewSet(viewsets.ModelViewSet):
    queryset = User.objects.all()
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = UserSerializer
    parser_classes = (MultiPartParser, JSONParser)

    def get_queryset(self):
        return User.objects.filter(id=self.request.user.id)

    @action(detail=False, methods=['put'], permission_classes=[permissions.IsAuthenticated])
    def reset_password(self, request):
        user: User = request.user
        user.set_password(request.data.get("password"))
        user.save()
        return Response(UserSerializer(user).data)

    def create(self, request, *args, **kwargs):
        return Response(status=status.HTTP_405_METHOD_NOT_ALLOWED)

    @action(detail=False, methods=['post'], permission_classes=[permissions.AllowAny])
    def register(self, request):
        token = request.data.get("token", None)
        if token is None:
            return Response({'error': 'Invalid token'}, status=status.HTTP_400_BAD_REQUEST)
        signer = TimestampSigner()
        try:
            email = signer.unsign(token, max_age=60*60*24*7)  # 1 week
            user = User.objects.create_user(email=email, username=email, password=request.data.get("password"))
            return Response(UserSerializer(user).data)
        except BadSignature:
            return Response({'error': 'Invalid or expired token'}, status=status.HTTP_400_BAD_REQUEST)


    def update(self, request, *args, **kwargs):
        user = request.user
        if "first_name" in request.data:
            user.first_name = request.data.get("first_name")
        if "last_name" in request.data:
            user.last_name = request.data.get("last_name")
        if "email" in request.data:
            user.email = request.data.get("email")
        user.save()
        return Response(UserSerializer(user).data)


class LogoutView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    parser_classes = (MultiPartParser, JSONParser)

    def post(self, request):
        return Response(status=status.HTTP_200_OK)