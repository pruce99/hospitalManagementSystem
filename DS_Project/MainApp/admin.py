from django.contrib import admin
from .models import PatientInformation, Logs

# Register your models here.

admin.site.register(PatientInformation)
admin.site.register(Logs)
