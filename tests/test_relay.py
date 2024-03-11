import json

import pytest
from django.db.models import Count
from graphql_relay import to_global_id
from graphql_relay.utils import unbase64

from tests.example.models import Apartment, Building, HousingCompany, PropertyManager
from tests.example.types import ApartmentNode, BuildingNode
from tests.example.utils import capture_database_queries

pytestmark = pytest.mark.django_db


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

    queries = len(results.queries)
    # 1 query for fetching Apartment and related Buildings
    assert queries == 1, results.log


def test_optimizer__relay_node__deep(client_query):
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

    queries = len(results.queries)
    # 1 query for fetching Apartment and related Buildings
    # 1 query for fetching Sales
    # 1 query for fetching Ownerships and related Owners
    assert queries == 3, results.log


def test_optimizer__relay_node__object_type_has_id_filter(client_query):
    building_id: int = Building.objects.values_list("id", flat=True).first()
    global_id = to_global_id(str(BuildingNode), building_id)

    # Test that for nodes, we don't run the `filterset_class` filters.
    # This would result in an error, since the ID for nodes is a global ID, and not a primary key.
    query = """
        query {
          building(id: "%s") {
            id
          }
        }
    """ % (global_id,)

    with capture_database_queries() as results:
        response = client_query(query)

    content = json.loads(response.content)
    assert "errors" not in content, content["errors"]

    queries = len(results.queries)
    # 1 query for fetching Buildings
    assert queries == 1, results.log


def test_optimizer__relay_node__object_type_has_id_filter__nested_filtering(client_query):
    buildings = Building.objects.alias(count=Count("apartments")).filter(count__gte=2)
    building_id: int = buildings.values_list("id", flat=True).first()

    apartments = list(Apartment.objects.filter(building_id=building_id))
    assert len(apartments) >= 2

    global_id = to_global_id(str(BuildingNode), building_id)

    # Check that for nested connections in relay nodes, we still run the filters.
    query = """
        query {
          building(id: "%s") {
            id
            apartments(streetAddress:"%s") {
              edges {
                node {
                  id
                  streetAddress
                }
              }
            }
          }
        }
    """ % (global_id, apartments[0].street_address)

    with capture_database_queries() as results:
        response = client_query(query)

    content = json.loads(response.content)
    assert "errors" not in content, content["errors"]

    queries = len(results.queries)
    # 1 query for fetching Buildings
    # 1 query for fetching Apartments
    assert queries == 2, results.log

    # Check that the nested filter is actually applied
    edges = content["data"]["building"]["apartments"]["edges"]
    assert len(edges) == 1
    assert edges[0]["node"]["streetAddress"] == apartments[0].street_address


# Connection


def test_optimizer__relay_connection(client_query):
    query = """
        query {
          pagedApartments {
            edges {
              node {
                id
                streetAddress
                building {
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
    # 1 query for counting Apartments
    # 1 query for fetching Apartments and related Buildings
    assert queries == 2, results.log


def test_optimizer__relay_connection__deep(client_query):
    query = """
        query {
          pagedApartments {
            edges {
              node {
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
          }
        }
    """

    with capture_database_queries() as results:
        response = client_query(query)

    content = json.loads(response.content)
    assert "errors" not in content, content["errors"]

    queries = len(results.queries)
    # 1 query for counting Apartments
    # 1 query for fetching Apartments and related Buildings
    # 1 query for fetching Sales
    # 1 query for fetching Ownerships and related Owners
    assert queries == 4, results.log


def test_optimizer__relay_connection__no_related_name(client_query):
    query = """
        query {
          pagedRealEstates {
            edges {
              node {
                buildingSet {
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

    queries = len(results.queries)
    # 1 query to count all real estates
    # 1 query to fetch real estates
    # 1 query to fetch buildings
    assert queries == 3, results.log


def test_optimizer__relay_connection__no_edges_from_connection_field(client_query):
    query = """
        query {
          pagedApartments {
            totalCount
            edgeCount
          }
        }
    """

    with capture_database_queries() as results:
        response = client_query(query)

    content = json.loads(response.content)
    assert "errors" not in content, content["errors"]

    assert content["data"]["pagedApartments"]["totalCount"] == Apartment.objects.count()
    assert content["data"]["pagedApartments"]["edgeCount"] == min(Apartment.objects.count(), 100)

    queries = len(results.queries)
    # 1 query for counting Apartments
    # 1 query for fetching Apartments (still made even if nothing is returned from it)
    assert queries == 2, results.log


def test_optimizer__relay_connection__no_node_from_edges(client_query):
    query = """
        query {
          pagedApartments {
            edges {
              cursor
            }
          }
        }
    """

    with capture_database_queries() as results:
        response = client_query(query)

    content = json.loads(response.content)
    assert "errors" not in content, content["errors"]

    queries = len(results.queries)
    # 1 query for counting Apartments
    # 1 query for fetching Apartments (still made even if nothing is returned from it)
    assert queries == 2, results.log


def test_optimizer__relay_connection__cursor_before_node(client_query):
    query = """
        query {
          pagedApartments {
            edges {
              cursor
              node {
                id
                building {
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
    # 1 query for counting Apartments
    # 1 query for fetching Apartments and related Buildings
    assert queries == 2, results.log


def test_optimizer__relay_connection__total_count_and_edge_count_before_edges(client_query):
    query = """
        query {
          pagedPropertyManagers {
            totalCount
            edgeCount
            edges {
              node {
                id
                housingCompanies {
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

    assert content["data"]["pagedPropertyManagers"]["totalCount"] == PropertyManager.objects.count()
    assert content["data"]["pagedPropertyManagers"]["edgeCount"] == min(PropertyManager.objects.count(), 100)

    queries = len(results.queries)
    # 1 query for counting Property Managers
    # 1 query for fetching Property Managers
    # 1 query for fetching Housing Companies
    assert queries == 3, results.log

    # Check that nested connection does not fetch the total count when not selected
    assert "SELECT COUNT(*) FROM" not in results.queries[2], results.log


def test_optimizer__relay_connection__total_count_and_edge_count_before_edges__nested(client_query):
    query = """
        query {
          pagedPropertyManagers(first:2) {
            edges {
              node {
                id
                housingCompanies(first:1) {
                  totalCount
                  edgeCount
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

    assert len(content["data"]["pagedPropertyManagers"]["edges"]) == 2

    node_1 = content["data"]["pagedPropertyManagers"]["edges"][0]["node"]
    node_2 = content["data"]["pagedPropertyManagers"]["edges"][1]["node"]

    pk_1 = int(unbase64(node_1["id"]).split(":")[-1])
    pk_2 = int(unbase64(node_2["id"]).split(":")[-1])

    count_1 = PropertyManager.objects.filter(pk=pk_1).first().housing_companies.count()
    count_2 = PropertyManager.objects.filter(pk=pk_2).first().housing_companies.count()

    assert node_1["housingCompanies"]["totalCount"] == count_1
    assert node_1["housingCompanies"]["edgeCount"] == 1

    assert node_2["housingCompanies"]["totalCount"] == count_2
    assert node_2["housingCompanies"]["edgeCount"] == 1

    queries = len(results.queries)
    # 1 query for counting Property Managers
    # 1 query for fetching Property Managers
    # 1 query for fetching Housing Companies (and counting them in a subquery)
    assert queries == 3, results.log

    # Check that nested connection fetches the total count when selected
    assert "SELECT COUNT(*) FROM" in results.queries[2], results.log


def test_optimizer__relay_connection__filtering(client_query):
    street_address: str = Apartment.objects.values_list("street_address", flat=True).first()

    query = """
        query {
          pagedApartments(streetAddress: "%s") {
            edges {
              node {
                id
                streetAddress
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

    queries = len(results.queries)
    # 1 query for counting Apartments
    # 1 query for fetching Apartments and related Buildings
    assert queries == 2, results.log


def test_optimizer__relay_connection__filtering_nested(client_query):
    building_name: str = (
        Building.objects.alias(count=Count("apartments")).filter(count__gt=1).values_list("name", flat=True).first()
    )

    query = """
        query {
          pagedApartments(building_Name: "%s") {
            edges {
              node {
                id
                streetAddress
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

    queries = len(results.queries)
    # 1 query for counting Apartments
    # 1 query for fetching Apartments and related Buildings
    assert queries == 2, results.log


def test_optimizer__relay_connection__filtering_empty(client_query):
    query = """
        query {
          pagedApartments(building_Name: "%s") {
            edges {
              node {
                id
                streetAddress
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

    queries = len(results.queries)
    # 1 query for counting Apartments
    assert queries == 1, results.log


# Nested


def test_optimizer__relay_connection__nested(client_query):
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
    # 1 query for fetching RealEstates
    assert queries == 3, results.log
    # Check that nested connection is limited even without any pagination args (based on settings)
    match = (
        "ROW_NUMBER() OVER "
        '(PARTITION BY "example_apartment"."building_id" '
        'ORDER BY "example_apartment"."street_address", "example_apartment"."stair", '
        '"example_apartment"."apartment_number" DESC)'
    )
    assert match in results.queries[2], results.log


def test_optimizer__relay_connection__nested__many_to_many(client_query):
    query = """
        query {
          pagedHousingCompanies {
            edges {
              node {
                name
                developers {
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

    queries = len(results.queries)
    # 1 query for counting HousingCompanies
    # 1 query for fetching HousingCompanies
    # 1 query for fetching RealEstates
    assert queries == 3, results.log
    # Check that nested connection is limited even without any pagination args (based on settings)


def test_optimizer__relay_connection__nested__paginated(client_query):
    query = """
        query {
          pagedBuildings(first: 5) {
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

    buildings = content["data"]["pagedBuildings"]["edges"]

    # Check that filtering worked
    assert len(buildings) == 5
    assert all(len(building["node"]["apartments"]["edges"]) == 1 for building in buildings), buildings

    queries = len(results.queries)
    # 1 query for counting Buildings
    # 1 query for fetching Buildings
    # 1 query for fetching Apartments
    assert queries == 3, results.log
    # Check that nested connection is limited with pagination
    match = (
        "ROW_NUMBER() OVER "
        '(PARTITION BY "example_apartment"."building_id" '
        'ORDER BY "example_apartment"."street_address", "example_apartment"."stair", '
        '"example_apartment"."apartment_number" DESC)'
    )
    assert match in results.queries[2], results.log


def test_optimizer__relay_connection__nested__paginated__custom_ordering(client_query):
    manager_second = PropertyManager.objects.order_by("name")[1:].first()
    apartment_first = manager_second.housing_companies.order_by("street_address").first()
    apartment_last = manager_second.housing_companies.order_by("street_address").last()

    query_1 = """
        query {
          pagedPropertyManagers(first:1 offset:1 orderBy:"name") {
            edges {
              node {
                pk
                name
                housingCompanies(first:1 orderBy:"street_address") {
                  edges {
                    node {
                      pk
                      streetAddress
                    }
                  }
                }
              }
            }
          }
        }
    """

    with capture_database_queries() as results:
        response = client_query(query_1)

    content = json.loads(response.content)
    assert "errors" not in content, content["errors"]
    manager = content["data"]["pagedPropertyManagers"]["edges"][0]["node"]
    assert manager["name"] == manager_second.name
    apartment = manager["housingCompanies"]["edges"][0]["node"]
    assert apartment["pk"] == apartment_first.pk

    queries = len(results.queries)
    assert queries == 3, results.log
    # Check that nested connection is limited with pagination
    match = (
        "ROW_NUMBER() OVER ("
        'PARTITION BY "example_housingcompany"."property_manager_id" '
        'ORDER BY "example_housingcompany"."street_address")'
    )
    assert match in results.queries[2], results.log

    query_2 = """
        query {
          pagedPropertyManagers(first:1 offset:1 orderBy:"name") {
            edges {
              node {
                pk
                name
                housingCompanies(first:1 orderBy:"-street_address") {
                  edges {
                    node {
                      pk
                      streetAddress
                    }
                  }
                }
              }
            }
          }
        }
    """

    with capture_database_queries() as results:
        response = client_query(query_2)

    content = json.loads(response.content)
    assert "errors" not in content, content["errors"]
    manager = content["data"]["pagedPropertyManagers"]["edges"][0]["node"]
    assert manager["name"] == manager_second.name
    apartment = manager["housingCompanies"]["edges"][0]["node"]
    assert apartment["pk"] == apartment_last.pk

    queries = len(results.queries)
    assert queries == 3, results.log
    # Check that nested connection is limited with pagination
    match = (
        "ROW_NUMBER() OVER "
        '(PARTITION BY "example_housingcompany"."property_manager_id" '
        'ORDER BY "example_housingcompany"."street_address" DESC)'
    )
    assert match in results.queries[2], results.log


def test_optimizer__relay_connection__nested__paginated__last(client_query):
    query = """
        query {
          pagedBuildings(last: 5) {
            edges {
              node {
                pk
                apartments(last: 1) {
                  edges {
                    node {
                      pk
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

    buildings = content["data"]["pagedBuildings"]["edges"]

    # Check that filtering worked
    assert len(buildings) == 5
    assert all(len(building["node"]["apartments"]["edges"]) == 1 for building in buildings), buildings

    queries = len(results.queries)
    # 1 query for counting Buildings
    # 1 query for fetching Buildings
    # 1 query for fetching Apartments
    assert queries == 3, results.log
    # Check that nested connection is limited with pagination
    match = (
        "ROW_NUMBER() OVER "
        '(PARTITION BY "example_apartment"."building_id" '
        'ORDER BY "example_apartment"."street_address", "example_apartment"."stair", '
        '"example_apartment"."apartment_number" DESC)'
    )
    assert match in results.queries[2], results.log


def test_optimizer__relay_connection__nested__filtered(client_query):
    name = HousingCompany.objects.values_list("name", flat=True).first()
    query = """
        query {
          pagedPropertyManagers {
            edges {
              node {
                id
                housingCompanies(name_Iexact: "%s") {
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
    # Check that the filter is actually applied
    assert '"example_housingcompany"."name" LIKE' in results.queries[2], results.log


def test_optimizer__relay_connection__nested__filtered__deep(client_query):
    name = HousingCompany.objects.values_list("name", flat=True).first()
    query = """
        query {
          pagedPropertyManagers {
            edges {
              node {
                id
                housingCompanies(name_Iexact: "%s") {
                  edges {
                    node {
                      realEstates(first:1) {
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
    # 1 query for fetching Real Estates
    assert queries == 4, results.log

    # Check that the filter/pagination is actually applied to the last nested connection
    assert "ROW_NUMBER() OVER (PARTITION BY" in results.queries[3], results.log


def test_optimizer__relay_connection__nested__filtered_fragment_spread(client_query):
    name = HousingCompany.objects.values_list("name", flat=True).first()
    query = """
        fragment Companies on PropertyManagerNode {
          housingCompanies(name_Iexact: "%s") {
            edges {
              node {
                name
              }
            }
          }
        }
        query {
          pagedPropertyManagers {
            edges {
              node {
                id
                ...Companies
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
    # Check that the filter is actually applied
    assert '"example_housingcompany"."name" LIKE' in results.queries[2], results.log


@pytest.mark.usefixtures("_set_building_node_apartments_max_limit")
def test_optimizer__relay_connection__nested__max_limit(client_query):
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
          }
        }
    """

    with capture_database_queries() as results:
        response = client_query(query)

    content = json.loads(response.content)
    assert "errors" not in content, content["errors"]

    buildings = content["data"]["pagedBuildings"]["edges"]

    assert all(len(building["node"]["apartments"]["edges"]) == 1 for building in buildings)

    queries = len(results.queries)
    # 1 query for counting Buildings
    # 1 query for fetching Buildings
    # 1 query for fetching nested Apartments
    assert queries == 3, results.log


@pytest.mark.usefixtures("_remove_apartment_node_apartments_max_limit")
def test_optimizer__relay_connection__nested__max_limit__first(client_query):
    query = """
        query {
          pagedBuildings {
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

    queries = len(results.queries)
    # 1 query for counting Buildings
    # 1 query for fetching Buildings
    # 1 query for fetching nested Apartments
    assert queries == 3, results.log

    # Check that nested connection is limited
    match = (
        "ROW_NUMBER() OVER "
        '(PARTITION BY "example_apartment"."building_id" '
        'ORDER BY "example_apartment"."street_address", "example_apartment"."stair", '
        '"example_apartment"."apartment_number" DESC)'
    )
    assert match in results.queries[2], results.log
