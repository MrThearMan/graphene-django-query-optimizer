import json

import pytest

from tests.example.utils import capture_database_queries

pytestmark = pytest.mark.django_db


def test_optimizer__deep_query(client_query):
    query = """
        query {
          allApartments {
            streetAddress
            stair
            apartmentNumber
            building {
              name
              realEstate {
                name
                surfaceArea
                housingCompany {
                  name
                  streetAddress
                  postalCode {
                    code
                  }
                }
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
    # 1 query for fetching Apartments and related Buildings, RealEstates, HousingCompanies, and PostalCodes
    assert queries == 1, results.log


def test_optimizer__many_to_one_relations(client_query):
    query = """
        query {
          allApartments {
            streetAddress
            stair
            apartmentNumber
            sales {
              purchaseDate
              ownerships {
                percentage
                owner {
                  name
                }
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
    # 1 query for fetching Apartments
    # 1 query for fetching Sales
    # 1 query for fetching Ownerships and related Owners
    assert queries == 3, results.log
    # Check that no limiting is applied to the nested fields, since they are list fields
    assert "ROW_NUMBER() OVER" not in results.log, results.log


def test_optimizer__many_to_many_relations(client_query):
    query = """
        query {
          allHousingCompanies {
            name
            developers {
              name
              description
            }
          }
        }
    """

    with capture_database_queries() as results:
        response = client_query(query)

    content = json.loads(response.content)
    assert "errors" not in content, content["errors"]

    queries = len(results.queries)
    # 1 query for fetching HousingCompanies
    # 1 query for fetching Developers
    assert queries == 2, results.log
    # Check that no limiting is applied to the nested fields, since they are list fields
    assert "ROW_NUMBER() OVER" not in results.log, results.log


def test_optimizer__many_to_many_relations__no_related_name(client_query):
    query = """
        query {
          allDevelopers {
            housingcompanySet {
              name
            }
          }
        }
    """

    with capture_database_queries() as results:
        response = client_query(query)

    content = json.loads(response.content)
    assert "errors" not in content, content["errors"]

    queries = len(results.queries)
    # 1 query for fetching Developers
    # 1 query for fetching HousingCompanies
    assert queries == 2, results.log
