import pytest
from graphql_relay import to_global_id

from example_project.app.types import ApartmentNode, BuildingNode
from tests.factories import ApartmentFactory, BuildingFactory
from tests.helpers import has

pytestmark = [
    pytest.mark.django_db,
]


def test_relay__node(graphql_client):
    apartment = ApartmentFactory.create(building__name="1")
    global_id = to_global_id(str(ApartmentNode), apartment.pk)

    query = """
        query {
          apartment(id: "%s") {
            building {
              name
            }
          }
        }
    """ % (global_id,)

    response = graphql_client(query)
    assert response.no_errors, response.errors

    # 1 query for fetching apartment and related buildings
    assert response.queries.count == 1, response.queries.log

    assert response.queries[0] == has(
        'FROM "app_apartment"',
    )

    assert response.content == {"building": {"name": "1"}}


def test_relay__node__deep(graphql_client):
    apartment = ApartmentFactory.create(sales__ownerships__owner__name="1")
    global_id = to_global_id(str(ApartmentNode), apartment.pk)

    query = """
        query {
          apartment(id: "%s") {
            sales {
              ownerships {
                owner {
                  name
                }
              }
            }
          }
        }
    """ % (global_id,)

    response = graphql_client(query)
    assert response.no_errors, response.errors

    # 1 query for fetching the apartment.
    # 1 query for fetching sales.
    # 1 query for fetching ownerships and related owners.
    assert response.queries.count == 3, response.queries.log

    assert response.queries[0] == has(
        'FROM "app_apartment"',
    )
    assert response.queries[1] == has(
        'FROM "app_sale"',
    )
    assert response.queries[2] == has(
        'FROM "app_ownership"',
        'INNER JOIN "app_owner"',
    )

    assert response.content == {
        "sales": [
            {
                "ownerships": [
                    {"owner": {"name": "1"}},
                ],
            },
        ],
    }


def test_relay__node__doesnt_mess_up_filterset(graphql_client):
    building = BuildingFactory.create()
    global_id = to_global_id(str(BuildingNode), building.pk)

    # Test that for nodes, we don't run the `filterset_class` filters.
    # This would result in an error, since the ID for nodes is a global ID, and not a primary key.
    query = """
        query {
          building(id: "%s") {
            id
          }
        }
    """ % (global_id,)

    response = graphql_client(query)
    assert response.no_errors, response.errors

    # 1 query for fetching Buildings
    assert response.queries.count == 1, response.queries.log

    assert response.queries[0] == has(
        'FROM "app_building"',
    )

    assert response.content == {"id": global_id}


def test_relay__node__doesnt_mess_up_filterset__nested_filtering(graphql_client):
    building = BuildingFactory.create()
    ApartmentFactory.create(street_address="1", building=building)
    ApartmentFactory.create(street_address="2", building=building)

    global_id = to_global_id(str(BuildingNode), building.pk)

    # Check that for nested connections in relay nodes, we still run the filters.
    query = """
        query {
          building(id: "%s") {
            apartments(streetAddress:"1") {
              edges {
                node {
                  streetAddress
                }
              }
            }
          }
        }
    """ % (global_id,)

    response = graphql_client(query)
    assert response.no_errors, response.errors

    # 1 query for fetching buildings.
    # 1 query for fetching apartments.
    assert response.queries.count == 2, response.queries.log

    assert response.queries[0] == has(
        'FROM "app_building"',
    )
    assert response.queries[1] == has(
        'FROM "app_apartment"',
    )

    # Check that the nested filter is actually applied
    assert response.content == {"apartments": {"edges": [{"node": {"streetAddress": "1"}}]}}
