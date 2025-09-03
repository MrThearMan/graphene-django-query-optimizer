from __future__ import annotations

import pytest

from tests.factories import ApartmentFactory, DeveloperFactory, OwnerFactory, PropertyManagerFactory
from tests.helpers import has

pytestmark = [
    pytest.mark.django_db,
]


def test_fragment_spread(graphql_client):
    ApartmentFactory.create(shares_start=1, shares_end=2)
    ApartmentFactory.create(shares_start=3, shares_end=4)
    ApartmentFactory.create(shares_start=5, shares_end=6)

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

    response = graphql_client(query)
    assert response.no_errors, response.errors

    # 1 query for fetching apartments.
    assert response.queries.count == 1, response.queries.log

    assert response.queries[0] == has(
        'FROM "app_apartment"',
        '"app_apartment"."shares_start"',
        '"app_apartment"."shares_end"',
    )

    assert response.content == [
        {"sharesStart": 1, "sharesEnd": 2},
        {"sharesStart": 3, "sharesEnd": 4},
        {"sharesStart": 5, "sharesEnd": 6},
    ]


def test_fragment_spread__relations(graphql_client):
    ApartmentFactory.create(building__real_estate__housing_company__postal_code__code="00001")
    ApartmentFactory.create(building__real_estate__housing_company__postal_code__code="00002")
    ApartmentFactory.create(building__real_estate__housing_company__postal_code__code="00003")

    query = """
        query {
          allApartments {
            ...Address
          }
        }

        fragment Address on ApartmentType {
          building {
            realEstate {
              housingCompany {
                postalCode {
                  code
                }
              }
            }
          }
        }
    """

    response = graphql_client(query)
    assert response.no_errors, response.errors

    # 1 query for fetching apartments and related buildings, real estates, housing companies, and postal codes
    assert response.queries.count == 1, response.queries.log

    assert response.queries[0] == has(
        'FROM "app_apartment"',
        'INNER JOIN "app_building"',
        'INNER JOIN "app_realestate"',
        'INNER JOIN "app_housingcompany"',
        'INNER JOIN "app_postalcode"',
    )

    assert response.content == [
        {"building": {"realEstate": {"housingCompany": {"postalCode": {"code": "00001"}}}}},
        {"building": {"realEstate": {"housingCompany": {"postalCode": {"code": "00002"}}}}},
        {"building": {"realEstate": {"housingCompany": {"postalCode": {"code": "00003"}}}}},
    ]


def test_fragment_spread__one_to_many_relations(graphql_client):
    ApartmentFactory.create(sales__ownerships__owner__name="1")
    ApartmentFactory.create(sales__ownerships__owner__name="2")
    ApartmentFactory.create(sales__ownerships__owner__name="3")

    query = """
        query {
          allApartments {
            ...Sales
          }
        }

        fragment Sales on ApartmentType {
          sales {
            ownerships {
              owner {
                name
              }
            }
          }
        }
    """

    response = graphql_client(query)
    assert response.no_errors, response.errors

    # 1 query for fetching apartments.
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

    assert response.content == [
        {"sales": [{"ownerships": [{"owner": {"name": "1"}}]}]},
        {"sales": [{"ownerships": [{"owner": {"name": "2"}}]}]},
        {"sales": [{"ownerships": [{"owner": {"name": "3"}}]}]},
    ]


def test_fragment_spread__same_relation_in_multiple_fragments(graphql_client):
    ApartmentFactory.create(
        sales__purchase_date="2020-01-01",
        sales__purchase_price=100,
        sales__ownerships__percentage=10,
        sales__ownerships__owner__name="foo",
    )
    ApartmentFactory.create(
        sales__purchase_date="2020-01-02",
        sales__purchase_price=200,
        sales__ownerships__percentage=20,
        sales__ownerships__owner__name="bar",
    )
    ApartmentFactory.create(
        sales__purchase_date="2020-01-03",
        sales__purchase_price=300,
        sales__ownerships__percentage=30,
        sales__ownerships__owner__name="baz",
    )

    query = """
        query {
          allApartments {
            surfaceArea
            ...PurchaseData
            ...SalesData
          }
        }

        fragment PurchaseData on ApartmentType {
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

        fragment SalesData on ApartmentType {
          sales {
            purchasePrice
            apartment {
              sharesStart
              sharesEnd
            }
          }
        }
    """

    response = graphql_client(query)
    assert response.no_errors, response.errors

    # 1 query for fetching apartments
    # 1 query for fetching sales and apartments
    # 1 query for fetching ownerships and owners
    assert response.queries.count == 3, response.queries.log

    assert response.queries[0] == has(
        'FROM "app_apartment"',
    )
    assert response.queries[1] == has(
        "purchase_date",
        "purchase_price",
        'FROM "app_sale"',
        'INNER JOIN "app_apartment"',
    )
    assert response.queries[2] == has(
        'FROM "app_ownership"',
        'INNER JOIN "app_owner"',
    )


def test_inline_fragment(graphql_client):
    DeveloperFactory.create(name="1", housingcompany_set__name="1")
    PropertyManagerFactory.create(name="1", housing_companies__name="1")
    OwnerFactory.create(name="1", ownerships__percentage=100)

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

    response = graphql_client(query)
    assert response.no_errors, response.errors

    # 1 query for fetching developers.
    # 1 query for fetching housing companies for developers.
    # 1 query for fetching property managers.
    # 1 query for fetching housing companies for property managers.
    # 1 query for fetching owners.
    # 1 query for fetching ownerships for owners.
    assert response.queries.count == 6, response.queries.log

    assert response.queries[0] == has(
        'FROM "app_developer"',
    )
    assert response.queries[1] == has(
        'FROM "app_housingcompany"',
    )
    assert response.queries[2] == has(
        'FROM "app_propertymanager"',
    )
    assert response.queries[3] == has(
        'FROM "app_housingcompany"',
    )
    assert response.queries[4] == has(
        'FROM "app_owner"',
    )
    assert response.queries[5] == has(
        'FROM "app_ownership"',
    )


def test_inline_fragment__typename(graphql_client):
    DeveloperFactory.create(name="1", housingcompany_set__name="1")
    PropertyManagerFactory.create(name="1", housing_companies__name="1")

    query = """
        query {
          allPeople {
            __typename
            ... on DeveloperType {
              name
            }
            ... on PropertyManagerType {
              name
            }
          }
        }
    """

    response = graphql_client(query)
    assert response.no_errors, response.errors

    # 1 query for fetching developers.
    # 1 query for fetching property managers.
    # 1 query for fetching owners (even if not used in the query).
    assert response.queries.count == 3, response.queries.log
