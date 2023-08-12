import os
from typing import Callable

import pytest
from django.http import HttpResponse
from django.test.client import Client
from graphene_django.utils.testing import graphql_query
from pytest_django.plugin import _DatabaseBlocker

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "tests.project.settings")


@pytest.fixture(scope="session", autouse=True)
def setup_database(django_db_blocker: _DatabaseBlocker) -> None:
    """Setup database."""
    from django.core.management import call_command

    with django_db_blocker.unblock():
        call_command("migrate")
        call_command("create_test_data")


@pytest.fixture(scope="session")
def django_db_setup():
    """Setup read-only database."""


@pytest.fixture()
def db_access_without_rollback_and_truncate(request, django_db_setup, django_db_blocker):
    """Setup read-only database."""
    django_db_blocker.unblock()
    request.addfinalizer(django_db_blocker.restore)


@pytest.fixture()
def client_query(client: Client) -> Callable[..., HttpResponse]:
    def func(*args, **kwargs) -> HttpResponse:
        return graphql_query(*args, **kwargs, client=client)

    return func
