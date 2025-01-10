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
from ct.models import CONSURFModel, ConsurfJob, ProteinFastaDatabase
from ct.serializers import CONSURFModelSerializer, ProteinFastaDatabaseSerializer, ConsurfJobSerializer
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
        cu = ChunkedUpload.objects.get(id=upload_id)
        file_path = cu.file.path
        fasta_database = ProteinFastaDatabase(name=cu.filename)
        with open(file_path, "rb") as f:
            fasta_database.fasta_file.save(cu.filename, f)
        fasta_database.user = request.user
        fasta_database.save()
        return Response(ProteinFastaDatabaseSerializer(fasta_database).data)

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        instance.fasta_file.delete()
        return super().destroy(request, *args, **kwargs)


class ConsurfJobViewSet(viewsets.ModelViewSet):
    queryset = ConsurfJob.objects.all()
    serializer_class = ConsurfJobSerializer
    permission_classes = [permissions.IsAuthenticated]
    parser_classes = (MultiPartParser, JSONParser)

    def get_queryset(self):
        user_id = self.request.user.id
        return ConsurfJob.objects.filter(user_id=user_id)

    def create(self, request, *args, **kwargs):
        data = request.data
        sequence = data.get("query_sequence")
        alignment_program = data.get("alignment_program")
        fasta_database_id = data.get("fasta_database")
        fasta_database = ProteinFastaDatabase.objects.get(id=fasta_database_id, user=request.user)
        consurf_job = ConsurfJob(user=request.user, query_sequence=sequence, alignment_program=alignment_program, fasta_database=fasta_database)
        consurf_job.save()
        run_consurf_job.delay(consurf_job.id)
        return Response(ConsurfJobSerializer(consurf_job).data)


class LogoutView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    parser_classes = (MultiPartParser, JSONParser)

    def post(self, request):
        return Response(status=status.HTTP_200_OK)