from rest_framework import serializers
from ct.models import CONSURFModel, ProteinFastaDatabase, ConsurfJob

class CONSURFModelSerializer(serializers.ModelSerializer):
    class Meta:
        model = CONSURFModel
        fields = '__all__'

class ProteinFastaDatabaseSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProteinFastaDatabase
        fields = '__all__'

class ConsurfJobSerializer(serializers.ModelSerializer):
    class Meta:
        model = ConsurfJob
        fields = '__all__'