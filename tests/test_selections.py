import contextlib
from unittest.mock import patch

import pytest

from query_optimizer.selections import get_field_selections
from query_optimizer.typing import GQLInfo
from tests.factories import HousingCompanyFactory

pytestmark = [
    pytest.mark.django_db,
]


@contextlib.contextmanager
def mock_selections():
    selections = []

    def tracker(info: GQLInfo) -> list[str]:
        selections.extend(get_field_selections(info))
        return selections

    path = "tests.example.schema.get_field_selections"
    with patch(path, side_effect=tracker):
        yield selections


def test_get_field_selections__simple(graphql_client):
    HousingCompanyFactory.create(name="foo")

    query = """
        query {
          housingCompanyByName(name:"foo") {
            pk
          }
        }
    """

    with mock_selections() as selections:
        response = graphql_client(query)

    assert response.no_errors, response.errors

    assert selections == ["pk"]


def test_get_field_selections__one_to_one_related(graphql_client):
    HousingCompanyFactory.create(name="foo")

    query = """
        query {
          housingCompanyByName(name:"foo") {
            pk
            postalCode {
              code
            }
          }
        }
    """

    with mock_selections() as selections:
        response = graphql_client(query)

    assert response.no_errors, response.errors

    assert selections == ["pk", {"postal_code": ["code"]}]


def test_get_field_selections__one_to_many_related(graphql_client):
    HousingCompanyFactory.create(name="foo")

    query = """
        query {
          housingCompanyByName(name:"foo") {
            pk
            realEstates {
              pk
            }
          }
        }
    """

    with mock_selections() as selections:
        response = graphql_client(query)

    assert response.no_errors, response.errors

    assert selections == ["pk", {"real_estates": ["pk"]}]


def test_get_field_selections__many_to_many_related(graphql_client):
    HousingCompanyFactory.create(name="foo")

    query = """
        query {
          housingCompanyByName(name:"foo") {
            pk
            developers {
              pk
            }
          }
        }
    """

    with mock_selections() as selections:
        response = graphql_client(query)

    assert response.no_errors, response.errors

    assert selections == ["pk", {"developers": ["pk"]}]


def test_get_field_selections__plain_object_type(graphql_client):
    HousingCompanyFactory.create(name="foo")

    query = """
        query {
          plain {
            foo
          }
        }
    """

    with mock_selections() as selections:
        response = graphql_client(query)

    assert response.no_errors, response.errors

    assert selections == ["foo"]


def test_get_field_selections__plain_object_type__nested(graphql_client):
    HousingCompanyFactory.create(name="foo")

    query = """
        query {
          plain {
            foo
            bar {
              x
            }
          }
        }
    """

    with mock_selections() as selections:
        response = graphql_client(query)

    assert response.no_errors, response.errors

    assert selections == ["foo", {"bar": ["x"]}]
