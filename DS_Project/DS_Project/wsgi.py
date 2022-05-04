"""
WSGI config for DS_Project project.

It exposes the WSGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/4.0/howto/deployment/wsgi/
"""

import os
from django.core.wsgi import get_wsgi_application
import MainApp.raft as raft
from . import settings
from django.contrib.auth.models import User
from django.db.utils import IntegrityError

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'DS_Project.settings')

application = get_wsgi_application()

# create a superuser for debugging purposes
if settings.DEBUG:
    try:
        User.objects.create_superuser(username='superuser', password='superuser_password')
    except IntegrityError:
        pass


# start RAFT protocol
raft.main()
