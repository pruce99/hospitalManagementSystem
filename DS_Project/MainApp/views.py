from django.views import View
from django.shortcuts import render
from rest_framework import viewsets
from . import models
from . import serializers

# Create your views here.


class PatientInformationViewSet(viewsets.ModelViewSet):
    queryset = models.PatientInformation.objects.all()
    serializer_class = serializers.PatientInformationSerializer
