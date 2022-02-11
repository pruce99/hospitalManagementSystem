from django.views import View
from django.shortcuts import render
from rest_framework import viewsets
from . import models
from . import serializers

# Create your views here.


class TestView(View):
    # context variables
    message = 'Server is working!!'

    def get(self, request):
        return render(
            request,
            'test.html',
            context={
                'message': self.message,
            }
        )


class PatientInformationViewSet(viewsets.ModelViewSet):
    queryset = models.PatientInformation.objects.all()
    serializer_class = serializers.PatientInformationSerializer
