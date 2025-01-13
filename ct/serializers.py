from django.contrib.auth.models import User
from rest_framework import serializers
from ct.models import CONSURFModel, ProteinFastaDatabase, ConsurfJob, MultipleSequenceAlignment, StructureFile


class CONSURFModelSerializer(serializers.ModelSerializer):
    class Meta:
        model = CONSURFModel
        fields = '__all__'

class ProteinFastaDatabaseSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProteinFastaDatabase
        fields = '__all__'

class MultipleSequenceAlignmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = MultipleSequenceAlignment
        fields = ['id', 'name', 'msa_file', 'uploaded_at', 'user']

class StructureFileSerializer(serializers.ModelSerializer):
    class Meta:
        model = StructureFile
        fields = ['id', 'name', 'structure_file', 'uploaded_at', 'user', 'chains']

class ConsurfJobSerializer(serializers.ModelSerializer):
    class Meta:
        model = ConsurfJob
        fields = '__all__'

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['username', 'id', 'email', 'first_name', 'last_name']

