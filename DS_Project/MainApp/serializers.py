from rest_framework import serializers
from . import models


class PatientInformationSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.PatientInformation
        fields = ('first_name', 'last_name', 'age', 'gender', 'phone_number', 'email', 'department')
