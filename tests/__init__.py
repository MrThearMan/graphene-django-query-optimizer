import os

import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "app_project.config.settings")

django.setup()
