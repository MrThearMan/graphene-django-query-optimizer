import pytest

from tests.factories import ApartmentFactory, DeveloperFactory, HousingCompanyFactory, RealEstateFactory
from tests.helpers import has

pytestmark = [
    pytest.mark.django_db,
]


def test_relations__to_one_relations(graphql_client):
    ApartmentFactory.create(building__real_estate__housing_company__postal_code__code="00001")
    ApartmentFactory.create(building__real_estate__housing_company__postal_code__code="00002")
    ApartmentFactory.create(building__real_estate__housing_company__postal_code__code="00003")

    query = """
        query {
          allApartments {
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
        }
    """

    response = graphql_client(query)
    assert response.no_errors, response.errors

    # 1 query for fetching Apartments and related Buildings, RealEstates, HousingCompanies, and PostalCodes
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


def test_relations__one_to_many_relations(graphql_client):
    ApartmentFactory.create(sales__ownerships__owner__name="1")
    ApartmentFactory.create(sales__ownerships__owner__name="2")
    ApartmentFactory.create(sales__ownerships__owner__name="3")

    query = """
        query {
          allApartments {
            sales {
              ownerships {
                owner {
                  name
                }
              }
            }
          }
        }
    """

    response = graphql_client(query)
    assert response.no_errors, response.errors

    # 1 query for fetching Apartments
    # 1 query for fetching Sales
    # 1 query for fetching Ownerships and related Owners
    assert response.queries.count == 3, response.queries.log

    assert response.queries[0] == has('FROM "app_apartment"')
    assert response.queries[1] == has('FROM "app_sale"')
    assert response.queries[2] == has('FROM "app_ownership"', 'INNER JOIN "app_owner"')

    # Check that limiting is not applied to the nested fields, since they are list fields
    assert response.queries[1] != has("ROW_NUMBER() OVER")
    assert response.queries[2] != has("ROW_NUMBER() OVER")

    assert response.content == [
        {"sales": [{"ownerships": [{"owner": {"name": "1"}}]}]},
        {"sales": [{"ownerships": [{"owner": {"name": "2"}}]}]},
        {"sales": [{"ownerships": [{"owner": {"name": "3"}}]}]},
    ]


def test_relations__one_to_many_relations__no_related_name(graphql_client):
    RealEstateFactory.create(building_set__name="1")
    RealEstateFactory.create(building_set__name="2")
    RealEstateFactory.create(building_set__name="3")

    query = """
        query {
          allRealEstates {
            buildingSet {
              name
            }
          }
        }
    """

    response = graphql_client(query)
    assert response.no_errors, response.errors

    # 1 query for fetching RealEstates
    # 1 query for fetching Buildings
    assert response.queries.count == 2, response.queries.log

    assert response.queries[0] == has('FROM "app_realestate"')
    assert response.queries[1] == has('FROM "app_building"')

    # Check that limiting is not applied to the nested fields, since they are list fields
    assert response.queries[1] != has("ROW_NUMBER() OVER")

    assert response.content == [
        {"buildingSet": [{"name": "1"}]},
        {"buildingSet": [{"name": "2"}]},
        {"buildingSet": [{"name": "3"}]},
    ]


def test_relations__many_to_many_relations(graphql_client):
    HousingCompanyFactory.create(developers__name="1")
    HousingCompanyFactory.create(developers__name="2")
    HousingCompanyFactory.create(developers__name="3")

    query = """
        query {
          allHousingCompanies {
            developers {
              name
            }
          }
        }
    """

    response = graphql_client(query)
    assert response.no_errors, response.errors

    # 1 query for fetching HousingCompanies
    # 1 query for fetching Developers
    assert response.queries.count == 2, response.queries.log

    assert response.queries[0] == has('FROM "app_housingcompany"')
    assert response.queries[1] == has('FROM "app_developer"')

    # Check that limiting is not applied to the nested fields, since they are list fields
    assert response.queries[1] != has("ROW_NUMBER() OVER")

    assert response.content == [
        {"developers": [{"name": "1"}]},
        {"developers": [{"name": "2"}]},
        {"developers": [{"name": "3"}]},
    ]


def test_relations__many_to_many_relations__no_related_name(graphql_client):
    DeveloperFactory.create(housingcompany_set__name="1")
    DeveloperFactory.create(housingcompany_set__name="2")
    DeveloperFactory.create(housingcompany_set__name="3")

    query = """
        query {
          allDevelopers {
            housingcompanySet {
              name
            }
          }
        }
    """

    response = graphql_client(query)
    assert response.no_errors, response.errors

    # 1 query for fetching Developers
    # 1 query for fetching HousingCompanies
    assert response.queries.count == 2, response.queries.log

    assert response.queries[0] == has('FROM "app_developer"')
    assert response.queries[1] == has('FROM "app_housingcompany"')

    assert response.content == [
        {"housingcompanySet": [{"name": "1"}]},
        {"housingcompanySet": [{"name": "2"}]},
        {"housingcompanySet": [{"name": "3"}]},
    ]


def test_relations__many_to_many_relations__shared_entities(graphql_client):
    developer_1 = DeveloperFactory.create(name="1")
    developer_2 = DeveloperFactory.create(name="2")
    developer_3 = DeveloperFactory.create(name="3")
    developer_4 = DeveloperFactory.create(name="4")
    developer_5 = DeveloperFactory.create(name="5")
    developer_6 = DeveloperFactory.create(name="6")

    HousingCompanyFactory.create(developers=[developer_1, developer_2, developer_3])
    HousingCompanyFactory.create(developers=[developer_3, developer_5, developer_6])
    HousingCompanyFactory.create(developers=[developer_1, developer_3, developer_4, developer_6])

    query = """
        query {
          allHousingCompanies {
            developers {
              name
            }
          }
        }
    """

    response = graphql_client(query)
    assert response.no_errors, response.errors

    # 1 query for fetching HousingCompanies
    # 1 query for fetching Developers
    assert response.queries.count == 2, response.queries.log

    assert response.queries[0] == has('FROM "app_housingcompany"')
    assert response.queries[1] == has('FROM "app_developer"')

    # Check that limiting is not applied to the nested fields, since they are list fields
    assert response.queries[1] != has("ROW_NUMBER() OVER")

    assert response.content == [
        {
            "developers": [
                {"name": "1"},
                {"name": "2"},
                {"name": "3"},
            ]
        },
        {
            "developers": [
                {"name": "3"},
                {"name": "5"},
                {"name": "6"},
            ]
        },
        {
            "developers": [
                {"name": "1"},
                {"name": "3"},
                {"name": "4"},
                {"name": "6"},
            ]
        },
    ]
