import datetime

import pytest

from tests.factories import (
    ApartmentFactory,
    BuildingFactory,
    DeveloperFactory,
    HousingCompanyFactory,
    PropertyManagerFactory,
    SaleFactory,
)
from tests.helpers import has

pytestmark = [
    pytest.mark.django_db,
]


def test_fields__annotated_field(graphql_client):
    HousingCompanyFactory.create(name="1")
    HousingCompanyFactory.create(name="2")
    HousingCompanyFactory.create(name="3")

    query = """
        query {
          allHousingCompanies {
            greeting
          }
        }
    """

    response = graphql_client(query)
    assert response.no_errors, response.errors

    # 1 query for fetching housing companies.
    assert response.queries.count == 1, response.queries.log

    assert response.queries[0] == has(
        'FROM "example_housingcompany"',
        '"example_housingcompany"."name" AS "greeting"',
    )

    assert response.content == [
        {"greeting": "Hello 1!"},
        {"greeting": "Hello 2!"},
        {"greeting": "Hello 3!"},
    ]


def test_fields__annotated_field__annotation_needs_joins(graphql_client):
    BuildingFactory.create(real_estate__name="1")
    BuildingFactory.create(real_estate__name="2")
    BuildingFactory.create(real_estate__name="3")

    query = """
        query {
          allBuildings {
            realEstateName
          }
        }
    """

    response = graphql_client(query)
    assert response.no_errors, response.errors

    # 1 query for all buildings with the annotated field.
    assert response.queries.count == 1, response.queries.log

    assert response.queries[0] == has(
        'FROM "example_building"',
        'INNER JOIN "example_realestate"',
    )

    assert response.content == [
        {"realEstateName": "1"},
        {"realEstateName": "2"},
        {"realEstateName": "3"},
    ]


def test_fields__annotated_field__in_relations(graphql_client):
    DeveloperFactory.create(housingcompany_set__name="1")
    DeveloperFactory.create(housingcompany_set__name="2")
    DeveloperFactory.create(housingcompany_set__name="3")

    query = """
        query {
          allDevelopers {
            housingcompanySet {
              greeting
            }
          }
        }
    """

    response = graphql_client(query)
    assert response.no_errors, response.errors

    # 1 query for fetching developers.
    # 1 query for fetching housing companies with the greeting field.
    assert response.queries.count == 2, response.queries.log

    assert response.queries[0] == has(
        'FROM "example_developer"',
    )
    assert response.queries[1] == has(
        'FROM "example_housingcompany"',
        'INNER JOIN "example_housingcompany_developers"',
        '"example_housingcompany"."name" AS "greeting"',
    )

    assert response.content == [
        {"housingcompanySet": [{"greeting": "Hello 1!"}]},
        {"housingcompanySet": [{"greeting": "Hello 2!"}]},
        {"housingcompanySet": [{"greeting": "Hello 3!"}]},
    ]


def test_fields__annotated_field__select_related_promoted_to_prefetch(graphql_client):
    SaleFactory.create(apartment__completion_date=datetime.date(2020, 1, 1))
    SaleFactory.create(apartment__completion_date=datetime.date(2021, 1, 1))
    SaleFactory.create(apartment__completion_date=datetime.date(2022, 1, 1))

    query = """
        query {
          allSales {
            apartment {
              completionYear
            }
          }
        }
    """

    response = graphql_client(query)
    assert response.no_errors, response.errors

    # 1 query for all buildings.
    # 1 query for all relates apartments with the annotated field.
    assert response.queries.count == 2, response.queries.log

    assert response.queries[0] == has(
        'FROM "example_sale"',
    )
    assert response.queries[1] == has(
        'FROM "example_apartment"',
        'django_date_extract(year, "example_apartment"."completion_date") AS "completion_year"',
    )

    assert response.content == [
        {"apartment": {"completionYear": 2020}},
        {"apartment": {"completionYear": 2021}},
        {"apartment": {"completionYear": 2022}},
    ]


def test_fields__annotated_field__aliases(graphql_client):
    HousingCompanyFactory.create(name="1")
    HousingCompanyFactory.create(name="2")
    HousingCompanyFactory.create(name="3")

    query = """
        query {
          allHousingCompanies {
            aliasGreeting
          }
        }
    """

    response = graphql_client(query)
    assert response.no_errors, response.errors

    # 1 query for fetching housing companies with the annotated field.
    assert response.queries.count == 1, response.queries.log

    assert response.queries[0] == has(
        'FROM "example_housingcompany"',
        '"example_housingcompany"."name" AS "alias_greeting"',
    )

    assert response.content == [
        {"aliasGreeting": "Hello 1!"},
        {"aliasGreeting": "Hello 2!"},
        {"aliasGreeting": "Hello 3!"},
    ]


def test_fields__alternate_field__to_one_relation(graphql_client):
    HousingCompanyFactory.create(property_manager__name="1")
    HousingCompanyFactory.create(property_manager__name="2")
    HousingCompanyFactory.create(property_manager__name="3")

    query = """
        query {
          pagedHousingCompanies {
            edges {
              node {
                propertyManagerAlt {
                  name
                }
              }
            }
          }
        }
    """

    response = graphql_client(query)
    assert response.no_errors, response.errors

    # 1 query for counting housing companies.
    # 1 query for fetching housing companies and related property managers.
    assert response.queries.count == 2, response.queries.log

    assert response.queries[0] == has(
        "COUNT(*)",
        'FROM "example_housingcompany"',
    )
    assert response.queries[1] == has(
        'FROM "example_housingcompany"',
        'INNER JOIN "example_propertymanager"',
    )

    assert response.content == {
        "edges": [
            {"node": {"propertyManagerAlt": {"name": "1"}}},
            {"node": {"propertyManagerAlt": {"name": "2"}}},
            {"node": {"propertyManagerAlt": {"name": "3"}}},
        ]
    }


def test_fields__alternate_field__one_to_many_related(graphql_client):
    HousingCompanyFactory.create(real_estates__name="1")
    HousingCompanyFactory.create(real_estates__name="2")
    HousingCompanyFactory.create(real_estates__name="3")

    query = """
        query {
          pagedHousingCompanies {
            edges {
              node {
                realEstatesAlt {
                  name
                }
              }
            }
          }
        }
    """

    response = graphql_client(query)
    assert response.no_errors, response.errors

    # 1 query for counting housing companies
    # 1 query for fetching housing companies
    # 1 query for fetching nested developers (to the alternate field)
    assert response.queries.count == 3, response.queries.log

    assert response.queries[0] == has(
        "COUNT(*)",
        'FROM "example_housingcompany"',
    )
    assert response.queries[1] == has(
        'FROM "example_housingcompany"',
    )
    assert response.queries[2] == has(
        'FROM "example_realestate"',
    )

    assert response.content == {
        "edges": [
            {"node": {"realEstatesAlt": [{"name": "1"}]}},
            {"node": {"realEstatesAlt": [{"name": "2"}]}},
            {"node": {"realEstatesAlt": [{"name": "3"}]}},
        ]
    }


def test_fields__alternate_field__many_to_many_related(graphql_client):
    HousingCompanyFactory.create(developers__name="1")
    HousingCompanyFactory.create(developers__name="2")
    HousingCompanyFactory.create(developers__name="3")

    query = """
        query {
          pagedHousingCompanies {
            edges {
              node {
                developersAlt {
                  name
                }
              }
            }
          }
        }
    """

    response = graphql_client(query)
    assert response.no_errors, response.errors

    # 1 query for counting housing companies
    # 1 query for fetching housing companies
    # 1 query for fetching nested developers (to the alternate field)
    assert response.queries.count == 3, response.queries.log

    assert response.queries[0] == has(
        "COUNT(*)",
        'FROM "example_housingcompany"',
    )
    assert response.queries[1] == has(
        'FROM "example_housingcompany"',
    )
    assert response.queries[2] == has(
        'FROM "example_developer"',
    )

    assert response.content == {
        "edges": [
            {"node": {"developersAlt": [{"name": "1"}]}},
            {"node": {"developersAlt": [{"name": "2"}]}},
            {"node": {"developersAlt": [{"name": "3"}]}},
        ]
    }


def test_fields__alternate_field__connection(graphql_client):
    PropertyManagerFactory.create(housing_companies__name="1")
    PropertyManagerFactory.create(housing_companies__name="2")
    PropertyManagerFactory.create(housing_companies__name="3")

    query = """
        query {
          pagedPropertyManagers {
            edges {
              node {
                housingCompaniesAlt {
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
    """

    response = graphql_client(query)
    assert response.no_errors, response.errors

    # 1 query for counting property managers
    # 1 query for fetching property managers
    # 1 query for fetching nested housing companies (to the alternate field)
    assert response.queries.count == 3, response.queries.log

    assert response.queries[0] == has(
        "COUNT(*)",
        'FROM "example_propertymanager"',
    )
    assert response.queries[1] == has(
        'FROM "example_propertymanager"',
    )
    assert response.queries[2] == has(
        'FROM "example_housingcompany"',
    )

    assert response.content == {
        "edges": [
            {"node": {"housingCompaniesAlt": {"edges": [{"node": {"name": "1"}}]}}},
            {"node": {"housingCompaniesAlt": {"edges": [{"node": {"name": "2"}}]}}},
            {"node": {"housingCompaniesAlt": {"edges": [{"node": {"name": "3"}}]}}},
        ]
    }


def test_fields__multi_field(graphql_client):
    ApartmentFactory.create(shares_start=1, shares_end=2)
    ApartmentFactory.create(shares_start=3, shares_end=4)
    ApartmentFactory.create(shares_start=5, shares_end=6)

    query = """
        query {
          allApartments {
            shareRange
          }
        }
    """

    response = graphql_client(query)
    assert response.no_errors, response.errors

    # 1 query for fetching Apartments
    assert response.queries.count == 1, response.queries.log

    assert response.queries[0] == has(
        'FROM "example_apartment"',
        '"example_apartment"."shares_start"',
        '"example_apartment"."shares_end"',
    )

    assert response.content == [
        {"shareRange": "1 - 2"},
        {"shareRange": "3 - 4"},
        {"shareRange": "5 - 6"},
    ]
