import json

import pytest

from tests.example.models import HousingCompany
from tests.example.utils import capture_database_queries

pytestmark = pytest.mark.django_db


def test_optimizer__filter__to_one_relation(client_query):
    postal_code = HousingCompany.objects.values_list("postal_code__code", flat=True).first()

    query = """
        query {
          pagedHousingCompanies(postalCode_Code_Iexact: "%s") {
            edges {
              node {
                name
                streetAddress
                postalCode {
                  code
                }
                city
                developers {
                  edges {
                    node {
                      name
                      description
                    }
                  }
                }
              }
            }
          }
        }
    """ % (postal_code,)

    with capture_database_queries() as results:
        response = client_query(query)

    content = json.loads(response.content)
    assert "errors" not in content, content["errors"]

    queries = len(results.queries)
    # 1 query for counting HousingCompanies
    # 1 query for fetching HousingCompanies and related PostalCodes
    # 1 query for fetching Developers
    assert queries == 3, results.log


def test_optimizer__filter__to_many_relation(client_query):
    developer_name = HousingCompany.objects.values_list("developers__name", flat=True).first()

    query = """
        query {
          pagedHousingCompanies(developers_Name_Iexact: "%s") {
            edges {
              node {
                name
                streetAddress
                city
              }
            }
          }
        }
    """ % (developer_name,)

    with capture_database_queries() as results:
        response = client_query(query)

    content = json.loads(response.content)
    assert "errors" not in content, content["errors"]

    queries = len(results.queries)
    # 1 query for counting HousingCompanies
    # 1 query for fetching HousingCompanies
    assert queries == 2, results.log


def test_optimizer__filter__order_by(client_query):
    query = """
        query {
          pagedHousingCompanies(orderBy: "name") {
            edges {
              node {
                name
                streetAddress
                city
              }
            }
          }
        }
    """

    with capture_database_queries() as results:
        response = client_query(query)

    content = json.loads(response.content)
    assert "errors" not in content, content["errors"]

    queries = len(results.queries)
    # 1 query for counting HousingCompanies
    # 1 query for fetching HousingCompanies
    assert queries == 2, results.log
