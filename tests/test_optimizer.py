import json

import graphene_django
import pytest
from django.db import models
from django.db.models import Count
from django.db.models.functions import RowNumber
from graphql_relay import to_global_id

from tests.example.models import (
    Apartment,
    Building,
    HousingCompany,
)
from tests.example.types import ApartmentNode
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
    assert "data" in content, content
    assert "allApartments" in content["data"], content["data"]
    apartments = content["data"]["allApartments"]
    assert len(apartments) != 0, apartments

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
    assert "data" in content, content
    assert "allApartments" in content["data"], content["data"]
    apartments = content["data"]["allApartments"]
    assert len(apartments) != 0, apartments

    queries = len(results.queries)
    # 1 query for fetching Apartments
    # 1 query for fetching Sales
    # 1 query for fetching Ownerships and related Owners
    assert queries == 3, results.log


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
    assert "data" in content, content
    assert "allHousingCompanies" in content["data"], content["data"]
    housing_companies = content["data"]["allHousingCompanies"]
    assert len(housing_companies) != 0, housing_companies

    queries = len(results.queries)
    # 1 query for fetching HousingCompanies
    # 1 query for fetching Developers
    assert queries == 2, results.log


def test_optimizer__all_relation_types(client_query):
    query = """
        query {
          examples {
            name
            forwardOneToOneField {
              name
            }
            forwardManyToOneField {
              name
            }
            forwardManyToManyFields {
              name
            }
            reverseOneToOneRel {
              name
            }
            reverseOneToManyRels {
              name
            }
            reverseManyToManyRels {
              name
            }
          }
        }
    """

    with capture_database_queries() as results:
        response = client_query(query)

    content = json.loads(response.content)
    assert "errors" not in content, content["errors"]
    assert "data" in content, content
    assert "examples" in content["data"], content["data"]
    assert len(content["data"]["examples"]) != 0, content

    queries = len(results.queries)
    # 1 query for all examples wih forward one-to-one, forward many-to-one, and reverse one-to-one relations
    # 1 query for all forward many-to-many relations
    # 1 query for all reverse one-to-many relations
    # 1 query for all reverse many-to-many relations
    assert queries == 4, results.log


def test_optimizer__relay_node(client_query):
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
    """ % (global_id,)

    with capture_database_queries() as results:
        response = client_query(query)

    content = json.loads(response.content)
    assert "errors" not in content, content["errors"]
    assert "data" in content, content
    assert "apartment" in content["data"], content["data"]

    queries = len(results.queries)
    # 1 query for fetching Apartment and related Buildings
    assert queries == 1, results.log


@pytest.mark.skipif(
    condition=graphene_django.__version__.startswith("3.0."),
    reason="Issues in 'graphene_django' <3.1 with two GraphQLObjectTypes for one Model",
)
def test_optimizer__relay_node_deep(client_query):
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
    """ % (global_id,)

    with capture_database_queries() as results:
        response = client_query(query)

    content = json.loads(response.content)
    assert "errors" not in content, content["errors"]
    assert "data" in content, content
    assert "apartment" in content["data"], content["data"]

    queries = len(results.queries)
    # 1 query for fetching Apartment and related Buildings
    # 1 query for fetching Sales
    # 1 query for fetching Ownerships and related Owners
    assert queries == 3, results.log


def test_optimizer__relay_connection(client_query):
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

    with capture_database_queries() as results:
        response = client_query(query)

    content = json.loads(response.content)
    assert "errors" not in content, content["errors"]
    assert "data" in content, content
    assert "pagedApartments" in content["data"], content["data"]
    assert "edges" in content["data"]["pagedApartments"], content["data"]["pagedApartments"]
    apartments = content["data"]["pagedApartments"]["edges"]
    assert len(apartments) != 0, apartments

    queries = len(results.queries)
    # 1 query for counting Apartments
    # 1 query for fetching Apartments and related Buildings
    assert queries == 2, results.log


@pytest.mark.skipif(
    condition=graphene_django.__version__.startswith("3.0."),
    reason="Issues in 'graphene_django' <3.1 with two GraphQLObjectTypes for one Model",
)
def test_optimizer__relay_connection_deep(client_query):
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

    with capture_database_queries() as results:
        response = client_query(query)

    content = json.loads(response.content)
    assert "errors" not in content, content["errors"]
    assert "data" in content, content
    assert "pagedApartments" in content["data"], content["data"]
    assert "edges" in content["data"]["pagedApartments"], content["data"]["pagedApartments"]
    apartments = content["data"]["pagedApartments"]["edges"]
    assert len(apartments) != 0, apartments

    queries = len(results.queries)
    # 1 query for counting Apartments
    # 1 query for fetching Apartments and related Buildings
    # 1 query for fetching Sales
    # 1 query for fetching Ownerships and related Owners
    assert queries == 4, results.log


def test_optimizer__relay_connection_filtering(client_query):
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
    """ % (street_address,)

    with capture_database_queries() as results:
        response = client_query(query)

    content = json.loads(response.content)
    assert "errors" not in content, content["errors"]
    assert "data" in content, content
    assert "pagedApartments" in content["data"], content["data"]
    assert "edges" in content["data"]["pagedApartments"], content["data"]["pagedApartments"]
    apartments = content["data"]["pagedApartments"]["edges"]
    assert len(apartments) != 0, apartments

    queries = len(results.queries)
    # 1 query for counting Apartments
    # 1 query for fetching Apartments and related Buildings
    assert queries == 2, results.log


def test_optimizer__relay_connection_filtering_nested(client_query):
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
    """ % (building_name,)

    with capture_database_queries() as results:
        response = client_query(query)

    content = json.loads(response.content)
    assert "errors" not in content, content["errors"]
    assert "data" in content, content
    assert "pagedApartments" in content["data"], content["data"]
    assert "edges" in content["data"]["pagedApartments"], content["data"]["pagedApartments"]
    apartments = content["data"]["pagedApartments"]["edges"]
    assert len(apartments) != 0, apartments

    queries = len(results.queries)
    # 1 query for counting Apartments
    # 1 query for fetching Apartments and related Buildings
    assert queries == 2, results.log


def test_optimizer__relay_connection_filtering_empty(client_query):
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
    """ % ("foo",)

    with capture_database_queries() as results:
        response = client_query(query)

    content = json.loads(response.content)
    assert "errors" not in content, content["errors"]
    assert "data" in content, content
    assert "pagedApartments" in content["data"], content["data"]
    assert "edges" in content["data"]["pagedApartments"], content["data"]["pagedApartments"]
    apartments = content["data"]["pagedApartments"]["edges"]
    assert apartments == [], apartments

    queries = len(results.queries)
    # 1 query for counting Apartments
    assert queries == 1, results.log


def test_optimizer__relay_connection_nested(client_query):
    query = """
        query {
          pagedBuildings {
            edges {
              node {
                id
                apartments {
                  edges {
                    node {
                      id
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

    with capture_database_queries() as results:
        response = client_query(query)

    content = json.loads(response.content)
    assert "errors" not in content, content["errors"]

    assert "data" in content
    assert "pagedBuildings" in content["data"]
    assert "edges" in content["data"]["pagedBuildings"]
    buildings = content["data"]["pagedBuildings"]["edges"]
    assert len(buildings) != 0, buildings

    assert "node" in buildings[0]
    assert "apartments" in buildings[0]["node"]
    assert "edges" in buildings[0]["node"]["apartments"]
    apartments = buildings[0]["node"]["apartments"]["edges"]
    assert len(apartments) != 0, apartments

    queries = len(results.queries)
    # 1 query for counting HousingCompanies
    # 1 query for fetching HousingCompanies
    # 1 query for fetching RealEstates
    assert queries == 3, results.log


def test_optimizer__relay_connection_nested__paginated(client_query):
    query = """
        query {
          pagedBuildings(first: 10) {
            edges {
              node {
                id
                apartments(first: 1) {
                  edges {
                    node {
                      id
                    }
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

    assert "data" in content
    assert "pagedBuildings" in content["data"]
    assert "edges" in content["data"]["pagedBuildings"]
    buildings = content["data"]["pagedBuildings"]["edges"]
    assert len(buildings) != 0, buildings

    assert len(buildings) == 10

    assert "node" in buildings[0]
    assert "apartments" in buildings[0]["node"]
    assert "edges" in buildings[0]["node"]["apartments"]
    apartments = buildings[0]["node"]["apartments"]["edges"]
    assert len(apartments) != 0, apartments

    # Check that filtering worked for the nested connection
    # (there are buildings with more than 1 apartment in the test data)
    assert all([len(building["node"]["apartments"]["edges"]) == 1 for building in buildings]), buildings

    queries = len(results.queries)
    # 1 query for counting Buildings
    # 1 query for fetching Buildings
    # 1 query for fetching Apartments
    assert queries == 3, results.log
    # TODO: assert "LIMIT 1" in results.queries[2], results.log


@pytest.mark.xfail(reason="Not implemented yet")
def test_optimizer__relay_connection_nested__filtered(client_query):
    # TODO: result cache is lost when filtering nested connections.
    name = HousingCompany.objects.values_list("name", flat=True).first()
    query = """
        query {
          pagedPropertyManagers {
            edges {
              node {
                id
                housingCompanies(
                  name_Iexact: "%s"
                ) {
                  edges {
                    node {
                      name
                    }
                  }
                }
              }
            }
          }
        }
    """ % (name,)

    with capture_database_queries() as results:
        response = client_query(query)

    content = json.loads(response.content)
    assert "errors" not in content, content["errors"]

    queries = len(results.queries)
    # 1 query for counting Property Managers
    # 1 query for fetching Property Managers
    # 1 query for fetching Housing Companies
    assert queries == 3, results.log


def test_optimizer__custom_fields(client_query):
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

    with capture_database_queries() as results:
        response = client_query(query)

    content = json.loads(response.content)
    assert "errors" not in content, content["errors"]
    assert "data" in content, content
    assert "allDevelopers" in content["data"], content["data"]
    developers = content["data"]["allDevelopers"]
    assert len(developers) != 0, developers

    queries = len(results.queries)
    # 1 query for fetching Developers
    # 1 query for fetching HousingCompanies with custom attributes
    assert queries == 2, results.log


def test_optimizer__custom_fields_one_to_many(client_query):
    query = """
        query {
          allHousingCompanies {
            primary
          }
        }
    """

    with capture_database_queries() as results:
        response = client_query(query)

    content = json.loads(response.content)
    assert "errors" not in content, content["errors"]
    assert "data" in content, content
    assert "allHousingCompanies" in content["data"], content["data"]
    developers = content["data"]["allHousingCompanies"]
    assert len(developers) != 0, developers

    queries = len(results.queries)
    # 1 query for fetching HousingCompanies
    # 1 query for fetching primary RealEstate
    assert queries == 2, results.log


def test_optimizer__custom_fields_backtracking(client_query):
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

    with capture_database_queries() as results:
        response = client_query(query)

    content = json.loads(response.content)
    assert "errors" not in content, content["errors"]
    assert "data" in content, content
    assert "allRealEstates" in content["data"], content["data"]
    developers = content["data"]["allRealEstates"]
    assert len(developers) != 0, developers

    queries = len(results.queries)
    # 1 query for fetching RealEstates and related HousingCompanies
    # 1 query for fetching primary RealEstate
    assert queries == 2, results.log


def test_optimizer__multiple_queries(client_query):
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

    with capture_database_queries() as results:
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
    # 1 query for fetching Apartments and related Buildings and RealEstates
    # 1 query for fetching RealEstates and related HousingCompanies
    assert queries == 2, results.log


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
    assert "data" in content, content
    assert "allApartments" in content["data"], content["data"]
    apartments = content["data"]["allApartments"]
    assert len(apartments) != 0, apartments

    queries = len(results.queries)
    # 1 query for fetching Apartments
    assert queries == 1, results.log


def test_optimizer__fragment_spread_deep(client_query):
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
    assert "data" in content, content
    assert "allApartments" in content["data"], content["data"]
    apartments = content["data"]["allApartments"]
    assert len(apartments) != 0, apartments

    queries = len(results.queries)
    # 1 query for fetching Apartments and related Buildings, RealEstates, HousingCompanies, and PostalCodes
    assert queries == 1, results.log


def test_optimizer__fragment_spread_many_to_one_relations(client_query):
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
    assert "data" in content, content
    assert "allApartments" in content["data"], content["data"]
    apartments = content["data"]["allApartments"]
    assert len(apartments) != 0, apartments

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

    with capture_database_queries() as results:
        response = client_query(query)

    content = json.loads(response.content)
    assert "errors" not in content, content["errors"]
    assert "data" in content, content
    assert "allPeople" in content["data"], content["data"]
    people = content["data"]["allPeople"]
    assert len(people) != 0, people

    queries = len(results.queries)
    # 1 query for fetching Developers
    # 1 query for fetching HousingCompanies for Developers
    # 1 query for fetching PropertyManagers
    # 1 query for fetching HousingCompanies for PropertyManagers
    # 1 query for fetching Owners
    # 1 query for fetching Ownerships for Owners
    assert queries == 6, results.log


@pytest.mark.skipif(
    condition=graphene_django.__version__.startswith("3.0."),
    reason="Issues in 'graphene_django' <3.1 with two GraphQLObjectTypes for one Model",
)
def test_optimizer__filter(client_query):
    postal_code = HousingCompany.objects.values_list("postal_code__code", flat=True).first()

    query = """
        query {
          pagedHousingCompanies(
            postalCode_Code_Iexact: "%s"
          ) {
            edges {
              node {
                name
                streetAddress
                postalCode {
                  code
                }
                city
                developers {
                  name
                  description
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
    assert "data" in content, content
    assert "pagedHousingCompanies" in content["data"], content["data"]
    assert "edges" in content["data"]["pagedHousingCompanies"], content["data"]["pagedHousingCompanies"]
    housing_companies = content["data"]["pagedHousingCompanies"]["edges"]
    assert len(housing_companies) != 0, housing_companies

    queries = len(results.queries)
    # 1 query for counting HousingCompanies
    # 1 query for fetching HousingCompanies and related PostalCodes
    # 1 query for fetching Developers
    assert queries == 3, results.log


def test_optimizer__filter_to_many_relations(client_query):
    developer_name = HousingCompany.objects.values_list("developers__name", flat=True).first()

    query = """
        query {
          pagedHousingCompanies(
            developers_Name_Iexact: "%s"
          ) {
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
    assert "data" in content, content
    assert "pagedHousingCompanies" in content["data"], content["data"]
    assert "edges" in content["data"]["pagedHousingCompanies"], content["data"]["pagedHousingCompanies"]
    housing_companies = content["data"]["pagedHousingCompanies"]["edges"]
    assert len(housing_companies) != 0, housing_companies

    queries = len(results.queries)
    # 1 query for counting HousingCompanies
    # 1 query for fetching HousingCompanies
    assert queries == 2, results.log


def test_optimizer__filter_order_by(client_query):
    query = """
        query {
          pagedHousingCompanies(
            orderBy: "name"
          ) {
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
    assert "data" in content, content
    assert "pagedHousingCompanies" in content["data"], content["data"]
    assert "edges" in content["data"]["pagedHousingCompanies"], content["data"]["pagedHousingCompanies"]
    housing_companies = content["data"]["pagedHousingCompanies"]["edges"]
    assert len(housing_companies) != 0, housing_companies

    queries = len(results.queries)
    # 1 query for counting HousingCompanies
    # 1 query for fetching HousingCompanies
    assert queries == 2, results.log


def test_optimizer__max_complexity_reached(client_query):
    query = """
        query {
          allApartments {
            building {
              apartments {
                building {
                  apartments {
                    building {
                      apartments {
                        building {
                          apartments {
                            building {
                              apartments {
                                 building {
                                  name
                                }
                              }
                            }
                          }
                        }
                      }
                    }
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
    assert "errors" in content, content["errors"]
    errors = content["errors"]
    assert len(errors) == 1, errors
    assert "message" in content["errors"][0], errors
    message = content["errors"][0]["message"]
    assert message == "Query complexity of 11 exceeds the maximum allowed of 10"

    assert "data" in content, content
    assert "allApartments" in content["data"], content["data"]
    apartments = content["data"]["allApartments"]
    assert apartments is None

    queries = len(results.queries)
    # No queries since fetching is stopped due to complexity
    assert queries == 0, results.log


def test_optimizer__deep_query__pks(client_query):
    query = """
        query {
          allApartments {
            pk
            building {
              pk
              realEstate {
                pk
                housingCompany {
                  pk
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
    assert "data" in content, content
    assert "allApartments" in content["data"], content["data"]
    apartments = content["data"]["allApartments"]
    assert len(apartments) != 0, apartments

    queries = len(results.queries)
    # 1 query for fetching Apartments and related Buildings, RealEstates, HousingCompanies, and PostalCodes
    assert queries == 1, results.log


def test_optimizer__annotated_value(client_query):
    query = """
        query {
          examples {
            foo
          }
        }
    """

    with capture_database_queries() as results:
        response = client_query(query)

    content = json.loads(response.content)
    assert "errors" not in content, content["errors"]

    # 1 query for all examples with the annotated values
    assert results.query_count == 1, results.log


def test_optimizer__select_related_promoted_to_prefetch_due_to_annotations(client_query):
    query = """
        query {
          examples {
            forwardManyToOneField {
              name
              bar
            }
          }
        }
    """

    with capture_database_queries() as results:
        response = client_query(query)

    content = json.loads(response.content)
    assert "errors" not in content, content["errors"]

    # 1 query for all examples
    # 1 query for fetching forward many-to-one relations with the annotations
    assert results.query_count == 2, results.log


def test_optimizer__limit_in_nested_connection_field__testing():
    # TODO: Nested connection fields need to be optimized when using `first` or `last` arguments
    #  We would need to generate the following windows function to the prefetch queryset.
    limit_parent = 2
    limit_child = 2

    buildings_1 = (
        Building.objects.prefetch_related(
            models.Prefetch(
                "apartments",
                queryset=(
                    Apartment.objects.alias(
                        _row_number=models.Window(
                            expression=RowNumber(),
                            partition_by=models.F("building_id"),
                        ),
                    )
                    # This doesn't support pagination fully, since you can't
                    # get the total count, or continue pagination from the last
                    # item in the previous page.
                    .filter(_row_number__lte=limit_child)
                    .only("pk", "building_id")
                ),
            )
        )
        .only("pk")
        .all()[:limit_parent]
    )

    with capture_database_queries() as count_1:
        builds_1 = list(buildings_1)
    print(count_1.log)
    assert count_1.query_count == 2, count_1.log

    assert len(builds_1) == limit_parent
    for build in builds_1:
        assert len(build.apartments.all()) <= limit_parent
