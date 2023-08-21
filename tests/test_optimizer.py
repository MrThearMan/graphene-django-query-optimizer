import json

import pytest
from django.db.models import Count
from graphql_relay import to_global_id

from tests.example.models import Apartment, Building
from tests.example.types import ApartmentNode
from tests.example.utils import count_queries

pytestmark = pytest.mark.django_db


def test_optimizer_deep_query(client_query):
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

    with count_queries() as results:
        response = client_query(query)

    content = json.loads(response.content)
    assert "errors" not in content, content["errors"]
    assert "data" in content, content
    assert "allApartments" in content["data"], content["data"]
    apartments = content["data"]["allApartments"]
    assert len(apartments) != 0, apartments

    queries = len(results.queries)
    assert queries == 1, results.message


def test_optimizer_many_to_one_relations(client_query):
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

    with count_queries() as results:
        response = client_query(query)

    content = json.loads(response.content)
    assert "errors" not in content, content["errors"]
    assert "data" in content, content
    assert "allApartments" in content["data"], content["data"]
    apartments = content["data"]["allApartments"]
    assert len(apartments) != 0, apartments

    queries = len(results.queries)
    assert queries == 3, results.message


def test_optimizer_many_to_many_relations(client_query):
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

    with count_queries() as results:
        response = client_query(query)

    content = json.loads(response.content)
    assert "errors" not in content, content["errors"]
    assert "data" in content, content
    assert "allHousingCompanies" in content["data"], content["data"]
    housing_companies = content["data"]["allHousingCompanies"]
    assert len(housing_companies) != 0, housing_companies

    queries = len(results.queries)
    assert queries == 2, results.message


def test_optimizer_relay_node(client_query):
    apartment_id: int = Apartment.objects.values_list("id", flat=True).first()
    global_id = to_global_id(str(ApartmentNode), apartment_id)

    query = """
        query {
          apartment(id: "%s") {
            id
            streetAddress
            building {
              name
            }
          }
        }
    """ % (
        global_id,
    )

    with count_queries() as results:
        response = client_query(query)

    content = json.loads(response.content)
    assert "errors" not in content, content["errors"]
    assert "data" in content, content
    assert "apartment" in content["data"], content["data"]

    queries = len(results.queries)
    assert queries == 1, results.message


def test_optimizer_relay_node_deep(client_query):
    apartment_id: int = Apartment.objects.values_list("id", flat=True).first()
    global_id = to_global_id(str(ApartmentNode), apartment_id)

    query = """
        query {
          apartment(id: "%s") {
            id
            streetAddress
            building {
              name
            }
            sales {
              ownerships {
                percentage
                owner {
                  name
                }
              }
            }
          }
        }
    """ % (
        global_id,
    )

    with count_queries() as results:
        response = client_query(query)

    content = json.loads(response.content)
    assert "errors" not in content, content["errors"]
    assert "data" in content, content
    assert "apartment" in content["data"], content["data"]

    queries = len(results.queries)
    assert queries == 3, results.message


def test_optimizer_relay_connection(client_query):
    query = """
        query {
          pagedApartments {
            edges {
              node {
                id,
                streetAddress,
                building {
                  name
                }
              }
            }
            pageInfo {
              hasNextPage
              endCursor
            }
          }
        }
    """

    with count_queries() as results:
        response = client_query(query)

    content = json.loads(response.content)
    assert "errors" not in content, content["errors"]
    assert "data" in content, content
    assert "pagedApartments" in content["data"], content["data"]
    assert "edges" in content["data"]["pagedApartments"], content["data"]["pagedApartments"]
    apartments = content["data"]["pagedApartments"]["edges"]
    assert len(apartments) != 0, apartments

    queries = len(results.queries)
    assert queries == 2, results.message


def test_optimizer_relay_connection_deep(client_query):
    query = """
        query {
          pagedApartments {
            edges {
              node {
                id,
                streetAddress,
                building {
                  name
                }
                sales {
                  ownerships {
                    percentage
                    owner {
                      name
                    }
                  }
                }
              }
            }
            pageInfo {
              hasNextPage
              endCursor
            }
          }
        }
    """

    with count_queries() as results:
        response = client_query(query)

    content = json.loads(response.content)
    assert "errors" not in content, content["errors"]
    assert "data" in content, content
    assert "pagedApartments" in content["data"], content["data"]
    assert "edges" in content["data"]["pagedApartments"], content["data"]["pagedApartments"]
    apartments = content["data"]["pagedApartments"]["edges"]
    assert len(apartments) != 0, apartments

    queries = len(results.queries)
    assert queries == 4, results.message


def test_optimizer_relay_connection_filtering(client_query):
    street_address: str = Apartment.objects.values_list("street_address", flat=True).first()

    query = """
        query {
          pagedApartments(streetAddress: "%s") {
            edges {
              node {
                id,
                streetAddress,
                building {
                  name
                }
              }
            }
          }
        }
    """ % (
        street_address,
    )

    with count_queries() as results:
        response = client_query(query)

    content = json.loads(response.content)
    assert "errors" not in content, content["errors"]
    assert "data" in content, content
    assert "pagedApartments" in content["data"], content["data"]
    assert "edges" in content["data"]["pagedApartments"], content["data"]["pagedApartments"]
    apartments = content["data"]["pagedApartments"]["edges"]
    assert len(apartments) != 0, apartments

    queries = len(results.queries)
    assert queries == 2, results.message


def test_optimizer_relay_connection_filtering_nested(client_query):
    building_name: str = (
        Building.objects.alias(count=Count("apartments")).filter(count__gt=1).values_list("name", flat=True).first()
    )

    query = """
        query {
          pagedApartments(building_Name: "%s") {
            edges {
              node {
                id,
                streetAddress,
                building {
                  name
                }
              }
            }
          }
        }
    """ % (
        building_name,
    )

    with count_queries() as results:
        response = client_query(query)

    content = json.loads(response.content)
    assert "errors" not in content, content["errors"]
    assert "data" in content, content
    assert "pagedApartments" in content["data"], content["data"]
    assert "edges" in content["data"]["pagedApartments"], content["data"]["pagedApartments"]
    apartments = content["data"]["pagedApartments"]["edges"]
    assert len(apartments) != 0, apartments

    queries = len(results.queries)
    assert queries == 2, results.message


def test_optimizer_relay_connection_filtering_empty(client_query):
    query = """
        query {
          pagedApartments(building_Name: "%s") {
            edges {
              node {
                id,
                streetAddress,
                building {
                  name
                }
              }
            }
          }
        }
    """ % (
        "foo",
    )

    with count_queries() as results:
        response = client_query(query)

    content = json.loads(response.content)
    assert "errors" not in content, content["errors"]
    assert "data" in content, content
    assert "pagedApartments" in content["data"], content["data"]
    assert "edges" in content["data"]["pagedApartments"], content["data"]["pagedApartments"]
    apartments = content["data"]["pagedApartments"]["edges"]
    assert apartments == [], apartments

    queries = len(results.queries)
    assert queries == 1, results.message


def test_optimizer_custom_fields(client_query):
    query = """
        query {
          allDevelopers {
            housingCompanies {
              greeting
              manager
            }
          }
        }
    """

    with count_queries() as results:
        response = client_query(query)

    content = json.loads(response.content)
    assert "errors" not in content, content["errors"]
    assert "data" in content, content
    assert "allDevelopers" in content["data"], content["data"]
    developers = content["data"]["allDevelopers"]
    assert len(developers) != 0, developers

    queries = len(results.queries)
    assert queries == 2, results.message


def test_optimizer_custom_fields_one_to_many(client_query):
    query = """
        query {
          allHousingCompanies {
            primary
          }
        }
    """

    with count_queries() as results:
        response = client_query(query)

    content = json.loads(response.content)
    assert "errors" not in content, content["errors"]
    assert "data" in content, content
    assert "allHousingCompanies" in content["data"], content["data"]
    developers = content["data"]["allHousingCompanies"]
    assert len(developers) != 0, developers

    queries = len(results.queries)
    assert queries == 2, results.message


def test_optimizer_custom_fields_backtracking(client_query):
    query = """
        query {
          allRealEstates {
            name
            housingCompany {
              primary
            }
          }
        }
    """

    with count_queries() as results:
        response = client_query(query)

    content = json.loads(response.content)
    assert "errors" not in content, content["errors"]
    assert "data" in content, content
    assert "allRealEstates" in content["data"], content["data"]
    developers = content["data"]["allRealEstates"]
    assert len(developers) != 0, developers

    queries = len(results.queries)
    assert queries == 2, results.message


def test_optimizer_multiple_queries(client_query):
    query = """
        query {
          allApartments {
            completionDate
            building {
              name
              realEstate {
                surfaceArea
              }
            }
          }
          allRealEstates {
            name
            housingCompany {
              streetAddress
            }
          }
        }
    """

    with count_queries() as results:
        response = client_query(query)

    content = json.loads(response.content)
    assert "errors" not in content, content["errors"]
    assert "data" in content, content
    assert "allApartments" in content["data"], content["data"]
    apartments = content["data"]["allApartments"]
    assert len(apartments) != 0, apartments
    assert "allRealEstates" in content["data"], content["data"]
    real_estates = content["data"]["allRealEstates"]
    assert len(real_estates) != 0, real_estates

    queries = len(results.queries)
    assert queries == 2, results.message


def test_optimizer_fragment_spread(client_query):
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

    with count_queries() as results:
        response = client_query(query)

    content = json.loads(response.content)
    assert "errors" not in content, content["errors"]
    assert "data" in content, content
    assert "allApartments" in content["data"], content["data"]
    apartments = content["data"]["allApartments"]
    assert len(apartments) != 0, apartments

    queries = len(results.queries)
    assert queries == 1, results.message


def test_optimizer_fragment_spread_deep(client_query):
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

    with count_queries() as results:
        response = client_query(query)

    content = json.loads(response.content)
    assert "errors" not in content, content["errors"]
    assert "data" in content, content
    assert "allApartments" in content["data"], content["data"]
    apartments = content["data"]["allApartments"]
    assert len(apartments) != 0, apartments

    queries = len(results.queries)
    assert queries == 1, results.message


def test_optimizer_fragment_spread_many_to_one_relations(client_query):
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

    with count_queries() as results:
        response = client_query(query)

    content = json.loads(response.content)
    assert "errors" not in content, content["errors"]
    assert "data" in content, content
    assert "allApartments" in content["data"], content["data"]
    apartments = content["data"]["allApartments"]
    assert len(apartments) != 0, apartments

    queries = len(results.queries)
    assert queries == 3, results.message


def test_optimizer_inline_fragment(client_query):
    query = """
        query {
          allPeople {
            ... on DeveloperType {
              name
              housingCompanies {
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

    with count_queries() as results:
        response = client_query(query)

    content = json.loads(response.content)
    assert "errors" not in content, content["errors"]
    assert "data" in content, content
    assert "allPeople" in content["data"], content["data"]
    people = content["data"]["allPeople"]
    assert len(people) != 0, people

    queries = len(results.queries)
    assert queries == 6, results.message
