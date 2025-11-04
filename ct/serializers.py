from django.contrib.auth.models import User
from rest_framework import serializers
from ct.models import CONSURFModel, ProteinFastaDatabase, ConsurfJob, MultipleSequenceAlignment, StructureFile


class CONSURFModelSerializer(serializers.ModelSerializer):
    class Meta:
        model = CONSURFModel
        fields = '__all__'

class ProteinFastaDatabaseSerializer(serializers.ModelSerializer):
    shared_with_usernames = serializers.SerializerMethodField()

    class Meta:
        model = ProteinFastaDatabase
        fields = '__all__'

    def get_shared_with_usernames(self, obj):
        return [user.username for user in obj.shared_with.all()]

class MultipleSequenceAlignmentSerializer(serializers.ModelSerializer):
    shared_with_usernames = serializers.SerializerMethodField()

    class Meta:
        model = MultipleSequenceAlignment
        fields = ['id', 'name', 'msa_file', 'uploaded_at', 'user', 'is_public', 'shared_with', 'shared_with_usernames']

    def get_shared_with_usernames(self, obj):
        return [user.username for user in obj.shared_with.all()]

class StructureFileSerializer(serializers.ModelSerializer):
    shared_with_usernames = serializers.SerializerMethodField()

    class Meta:
        model = StructureFile
        fields = ['id', 'name', 'structure_file', 'uploaded_at', 'user', 'chains', 'is_public', 'shared_with', 'shared_with_usernames']

    def get_shared_with_usernames(self, obj):
        return [user.username for user in obj.shared_with.all()]

class ConsurfJobSerializer(serializers.ModelSerializer):
    class Meta:
        model = ConsurfJob
        fields = '__all__'

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['username', 'id', 'email', 'first_name', 'last_name']

