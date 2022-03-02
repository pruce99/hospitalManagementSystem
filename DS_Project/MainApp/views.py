from django.views import View
from django.shortcuts import render
from rest_framework import viewsets
from rest_framework.views import APIView
from rest_framework.response import Response
from . import models
from . import serializers
import requests

# Create your views here.


class PatientInformationViewSet(viewsets.ModelViewSet):
    queryset = models.PatientInformation.objects.all()
    serializer_class = serializers.PatientInformationSerializer


class Leader(APIView):
    def post(self, request):
        nodes = [
            'backend2',
            'backend1',
            'backend',
        ]
        # make a call to all the nodes
        for node in nodes:
            response = requests.post(
                url=f'http://{node}:8000/MainApp/store_patient_info/',
                data=request.data,
            )
            if response.status_code != 201:
                return Response(data=None, status=400)
        return Response(data=None, status=201)
