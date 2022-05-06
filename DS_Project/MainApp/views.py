from django.views import View
from django.shortcuts import render
from rest_framework import viewsets
from rest_framework.views import APIView
from rest_framework.response import Response
from . import models
from . import serializers
import requests
from django.http import HttpResponse
import os
from MainApp import nodes
from . import raft
import socket
import json
import random
import threading

# Create your views here.
# ports
response_sock_port = 8999
# response_sock = socket.socket(family=socket.AF_INET, type=socket.SOCK_DGRAM)
# response_sock.bind((os.environ['node_id'], response_sock_port))
# response_receive_flag = False
# the_msg = {}  # dummy dict


# def response_listener(sock: socket.socket):
#     global the_msg
#     print('Starting response_listener')
#     while True:
#         response, addr = sock.recvfrom(1024)
#         response = json.loads(response.decode('utf-8'))  # decoded msg
#         if response['key'] == 'LEADER':
#             raft.udp_send(target=(response['value'], raft.controller_rpc_listener_port), msg=the_msg)
#             response, addr = response_sock.recvfrom(1024)
#             response = json.loads(response.decode('utf-8'))  # decoded msg


# start listeners
# threading.Thread(target=response_listener, args=[response_sock]).start()


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
        # raft.udp_send(target=(random.choice(nodes), raft.controller_rpc_listener_port), msg=the_msg)
        return Response(data=None, status=201)
