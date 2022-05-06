from rest_framework import viewsets
from rest_framework.views import APIView
from rest_framework.response import Response
from . import models
from . import serializers
from MainApp import nodes
from . import raft
import random
# Create your views here.


class PatientInformationViewSet(viewsets.ModelViewSet):
    queryset = models.PatientInformation.objects.all()
    serializer_class = serializers.PatientInformationSerializer


class Leader(APIView):
    def post(self, request):
        # global the_msg
        # the_msg = {
        #     'sender_name': os.environ['node_id'],
        #     'request': 'STORE',
        #     'key': 'store_data_' + request.data['first_name'],
        #     'value': request.data,
        # }
        raft.udp_send(target=(random.choice(nodes), raft.front_end_request_listener_port), msg=request.data)
        return Response(data=None, status=201)
