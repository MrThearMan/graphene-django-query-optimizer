import os

import pytest
from django.http import HttpResponse
from django.test.client import Client
from graphene_django.utils.testing import graphql_query

from query_optimizer.typing import Callable
from tests.example.types import BuildingNode

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "tests.project.settings")


@pytest.fixture(scope="session", autouse=True)
def setup_database(django_db_blocker, request) -> None:  # noqa: PT004
    """Setup database."""
    from django.core.management import call_command

    create_db: bool = request.config.getoption("--create-db")
    reuse_db: bool = request.config.getoption("--reuse-db")
    if reuse_db and not create_db:
        return

    no_migrations: bool = request.config.getoption("--no-migrations")
    with django_db_blocker.unblock():
        if not no_migrations or create_db:
            call_command("migrate")
        call_command("create_test_data")


@pytest.fixture(scope="session")
def django_db_setup():  # noqa: PT004
    """Setup read-only database."""


@pytest.fixture()
def db_access_without_rollback_and_truncate(request, django_db_setup, django_db_blocker):  # noqa: PT004
    """Setup read-only database."""
    django_db_blocker.unblock()
    request.addfinalizer(django_db_blocker.restore)  # noqa: PT021


@pytest.fixture()
def client_query(client: Client) -> Callable[..., HttpResponse]:
    def func(*args, **kwargs) -> HttpResponse:
        return graphql_query(*args, **kwargs, client=client)

    return func


@pytest.fixture()
def _set_building_node_apartments_max_limit() -> int:
    limit = BuildingNode.apartments.max_limit
    try:
        BuildingNode.apartments.max_limit = 1
        yield
    finally:
        BuildingNode.apartments.max_limit = limit


@pytest.fixture()
def _remove_apartment_node_apartments_max_limit() -> int:
    limit = BuildingNode.apartments.max_limit
    try:
        BuildingNode.apartments.max_limit = None
        yield
    finally:
        BuildingNode.apartments.max_limit = limit
