"""MainApp's URL Configuration

Write URL mappings of this app in this file

"""
from django.urls import path, include
from . import views
from rest_framework import routers

# set default router and register all api end-points here
router = routers.DefaultRouter()
router.register(r'patient_info', views.PatientInformationViewSet)

# Enable automatic URL routing for our API
urlpatterns = [
    # path('', views.TestView.as_view(), name='TestView'),
    path('', include(router.urls))
]
