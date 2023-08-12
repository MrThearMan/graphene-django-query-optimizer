from contextlib import suppress

from django.contrib import admin
from django.contrib.auth.models import User
from django.core.management import call_command
from django.urls import include, path
from graphene_django.views import GraphQLView

with suppress(Exception):
    call_command("makemigrations")
    call_command("migrate")
    if not User.objects.filter(username="x", email="user@user.com").exists():
        User.objects.create_superuser(username="x", email="user@user.com", password="x")


urlpatterns = [
    path("graphql", GraphQLView.as_view(graphiql=True)),
    path("admin/", admin.site.urls),
    path("__debug__/", include("debug_toolbar.urls")),
]
