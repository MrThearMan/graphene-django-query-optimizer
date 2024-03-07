import json

import pytest

from tests.example.utils import capture_database_queries

pytestmark = pytest.mark.django_db


def test_optimizer__fragment_spread(client_query):
    query = """
        query {
          allApartments {
            ...Shares
          }
        }

        fragment Shares on ApartmentType {
          sharesStart
          sharesEnd
        }
    """

    with capture_database_queries() as results:
        response = client_query(query)

    content = json.loads(response.content)
    assert "errors" not in content, content["errors"]

    queries = len(results.queries)
    # 1 query for fetching Apartments
    assert queries == 1, results.log


def test_optimizer__fragment_spread__deep(client_query):
    query = """
        query {
          allApartments {
            ...Address
          }
        }

        fragment Address on ApartmentType {
          streetAddress
          floor
          apartmentNumber
          building {
            realEstate {
              housingCompany {
                postalCode {
                  code
                }
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
    # 1 query for fetching Apartments and related Buildings, RealEstates, HousingCompanies, and PostalCodes
    assert queries == 1, results.log


def test_optimizer__fragment_spread__many_to_one_relations(client_query):
    query = """
        query {
          allApartments {
            ...Sales
          }
        }

        fragment Sales on ApartmentType {
          sales {
            purchaseDate
            purchasePrice
            ownerships {
              percentage
              owner {
                name
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


def test_optimizer__inline_fragment(client_query):
    query = """
        query {
          allPeople {
            ... on DeveloperType {
              name
              housingcompanySet {
                name
              }
              __typename
            }
            ... on PropertyManagerType {
              name
              housingCompanies {
                name
              }
              __typename
            }
            ... on OwnerType {
              name
              ownerships {
                percentage
              }
              __typename
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
    # 1 query for fetching HousingCompanies for Developers
    # 1 query for fetching PropertyManagers
    # 1 query for fetching HousingCompanies for PropertyManagers
    # 1 query for fetching Owners
    # 1 query for fetching Ownerships for Owners
    assert queries == 6, results.log
