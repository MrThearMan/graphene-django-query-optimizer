import pytest

from tests.factories import (
    ApartmentFactory,
    BuildingFactory,
    DeveloperFactory,
    HousingCompanyFactory,
    PostalCodeFactory,
    RealEstateFactory,
    TagFactory,
)
from tests.helpers import has

pytestmark = [
    pytest.mark.django_db,
]


def test_multiple_queries(graphql_client):
    ApartmentFactory.create(building__real_estate__name="1", building__real_estate__housing_company__name="1")
    ApartmentFactory.create(building__real_estate__name="2", building__real_estate__housing_company__name="2")
    ApartmentFactory.create(building__real_estate__name="3", building__real_estate__housing_company__name="3")

    query = """
        query {
          allApartments {
            building {
              realEstate {
                name
              }
            }
          }
          allRealEstates {
            housingCompany {
              name
            }
          }
        }
    """

    response = graphql_client(query)
    assert response.no_errors, response.errors

    # 1 query for fetching apartments and related buildings and real estates.
    # 1 query for fetching real estates and related housing companies.
    assert response.queries.count == 2, response.queries.log

    assert response.queries[0] == has(
        'FROM "example_apartment"',
        'INNER JOIN "example_building"',
        'INNER JOIN "example_realestate"',
    )
    assert response.queries[1] == has(
        'FROM "example_realestate"',
        'INNER JOIN "example_housingcompany"',
    )


def test_max_complexity_reached(graphql_client):
    ApartmentFactory.create()

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

    response = graphql_client(query)

    assert response.errors[0]["message"] == "Query complexity exceeds the maximum allowed of 10"

    # No queries are performed since fetching is stopped due to complexity.
    assert response.queries.count == 0, response.queries.log


def test_misc__pk_fields(graphql_client):
    ApartmentFactory.create(building__real_estate__housing_company__postal_code__code="00001")
    ApartmentFactory.create(building__real_estate__housing_company__postal_code__code="00002")
    ApartmentFactory.create(building__real_estate__housing_company__postal_code__code="00003")

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

    response = graphql_client(query)
    assert response.no_errors, response.errors

    # 1 query for fetching apartments and related buildings, real estates, housing companies, and postal codes
    assert response.queries.count == 1, response.queries.log

    assert response.queries[0] == has(
        'FROM "example_apartment"',
        'INNER JOIN "example_building"',
        'INNER JOIN "example_realestate"',
        'INNER JOIN "example_housingcompany"',
        'INNER JOIN "example_postalcode"',
        (
            '"example_building"."id", '
            '"example_building"."real_estate_id", '
            '"example_realestate"."id", '
            '"example_realestate"."housing_company_id", '
            '"example_housingcompany"."id", '
            '"example_housingcompany"."postal_code_id", '
            '"example_postalcode"."code"'
        ),
    )


def test_misc__to_many_objects_with_same_related_object(graphql_client):
    dev = DeveloperFactory.create(name="foo")
    postal_code = PostalCodeFactory.create(code="00001")

    HousingCompanyFactory.create(name="1", developers=[dev], postal_code=postal_code)
    HousingCompanyFactory.create(name="2", developers=[dev], postal_code=postal_code)
    HousingCompanyFactory.create(name="3", developers=[dev], postal_code=postal_code)

    query = """
        query {
          allHousingCompanies {
            name
            developers {
              name
            }
            postalCode {
              code
            }
          }
        }
    """

    response = graphql_client(query)
    assert response.no_errors, response.errors

    assert response.queries.count == 2, response.queries.log

    assert response.queries[0] == has(
        'FROM "example_housingcompany"',
        'INNER JOIN "example_postalcode"',
    )
    assert response.queries[1] == has(
        'FROM "example_developer"',
    )

    assert response.content == [
        {
            "name": "1",
            "postalCode": {"code": "00001"},
            "developers": [{"name": "foo"}],
        },
        {
            "name": "2",
            "postalCode": {"code": "00001"},
            "developers": [{"name": "foo"}],
        },
        {
            "name": "3",
            "postalCode": {"code": "00001"},
            "developers": [{"name": "foo"}],
        },
    ]


def test_misc__same_related_object_selected_with_different_fields_in_same_query(graphql_client):
    real_estate = RealEstateFactory.create(name="foo", surface_area=12)
    BuildingFactory.create(name="1", street_address="11", real_estate=real_estate)
    BuildingFactory.create(name="2", street_address="22", real_estate=real_estate)
    BuildingFactory.create(name="3", street_address="33", real_estate=real_estate)
    BuildingFactory.create(name="4", street_address="44", real_estate=real_estate)

    # Changing caching to pk based will
    query = """
        query {
          allRealEstates {
            name
            buildingSet {
              name
              realEstate {
                surfaceArea
                buildingSet {
                  streetAddress
                }
              }
            }
          }
        }
    """

    response = graphql_client(query)
    assert response.no_errors, response.errors

    assert response.queries.count == 3, response.queries.log

    assert response.queries[0] == has(
        'FROM "example_realestate"',
    )
    assert response.queries[1] == has(
        'FROM "example_building"',
        'INNER JOIN "example_realestate"',
    )
    assert response.queries[2] == has(
        'FROM "example_building"',
        b'INNER JOIN "example_realestate"',
    )

    assert response.content == [
        {
            "name": "foo",
            "buildingSet": [
                {
                    "name": "1",
                    "realEstate": {
                        "surfaceArea": "12.00",
                        "buildingSet": [
                            {"streetAddress": "11"},
                            {"streetAddress": "22"},
                            {"streetAddress": "33"},
                            {"streetAddress": "44"},
                        ],
                    },
                },
                {
                    "name": "2",
                    "realEstate": {
                        "surfaceArea": "12.00",
                        "buildingSet": [
                            {"streetAddress": "11"},
                            {"streetAddress": "22"},
                            {"streetAddress": "33"},
                            {"streetAddress": "44"},
                        ],
                    },
                },
                {
                    "name": "3",
                    "realEstate": {
                        "surfaceArea": "12.00",
                        "buildingSet": [
                            {"streetAddress": "11"},
                            {"streetAddress": "22"},
                            {"streetAddress": "33"},
                            {"streetAddress": "44"},
                        ],
                    },
                },
                {
                    "name": "4",
                    "realEstate": {
                        "surfaceArea": "12.00",
                        "buildingSet": [
                            {"streetAddress": "11"},
                            {"streetAddress": "22"},
                            {"streetAddress": "33"},
                            {"streetAddress": "44"},
                        ],
                    },
                },
            ],
        }
    ]


def test_misc__generic_relations(graphql_client):
    postal_code_1 = PostalCodeFactory.create(code="00001")
    postal_code_2 = PostalCodeFactory.create(code="00002")
    developer_1 = DeveloperFactory.create(name="foo")
    TagFactory.create(tag="1", content_object=postal_code_1)
    TagFactory.create(tag="2", content_object=postal_code_1)
    TagFactory.create(tag="3", content_object=postal_code_1)
    TagFactory.create(tag="4", content_object=postal_code_2)
    TagFactory.create(tag="5", content_object=developer_1)
    TagFactory.create(tag="6", content_object=developer_1)

    query = """
        query {
          allPostalCodes {
            code
            tags {
              tag
            }
          }
        }
    """

    response = graphql_client(query)
    assert response.no_errors, response.errors

    assert response.queries.count == 2, response.queries.log

    assert response.queries[0] == has(
        'FROM "example_postalcode"',
    )
    assert response.queries[1] == has(
        'FROM "example_tag"',
    )

    assert response.content == [
        {
            "code": "00001",
            "tags": [
                {"tag": "1"},
                {"tag": "2"},
                {"tag": "3"},
            ],
        },
        {
            "code": "00002",
            "tags": [
                {"tag": "4"},
            ],
        },
    ]


def test_misc__generic_foreign_key(graphql_client):
    postal_code_1 = PostalCodeFactory.create(code="00001")
    postal_code_2 = PostalCodeFactory.create(code="00002")
    developer_1 = DeveloperFactory.create(name="foo")
    TagFactory.create(tag="1", content_object=postal_code_1)
    TagFactory.create(tag="2", content_object=postal_code_1)
    TagFactory.create(tag="3", content_object=postal_code_1)
    TagFactory.create(tag="4", content_object=postal_code_2)
    TagFactory.create(tag="5", content_object=developer_1)
    TagFactory.create(tag="6", content_object=developer_1)

    query = """
        query {
          allTags {
            tag
            contentObject {
              ... on PostalCodeType {
                code
              }
              ... on DeveloperType {
                name
              }
            }
          }
        }
    """

    response = graphql_client(query)
    assert response.no_errors, response.errors

    assert response.queries.count == 3, response.queries.log

    assert response.queries[0] == has(
        'FROM "example_tag"',
    )
    assert response.queries[1] == has(
        'FROM "example_postalcode"',
    )
    assert response.queries[2] == has(
        'FROM "example_developer"',
    )

    assert response.content == [
        {"contentObject": {"code": "00001"}, "tag": "1"},
        {"contentObject": {"code": "00001"}, "tag": "2"},
        {"contentObject": {"code": "00001"}, "tag": "3"},
        {"contentObject": {"code": "00002"}, "tag": "4"},
        {"contentObject": {"name": "foo"}, "tag": "5"},
        {"contentObject": {"name": "foo"}, "tag": "6"},
    ]


@pytest.mark.skip(reason="Optimization requires `GenericPrefetch` from Django 5.0")
def test_misc__generic_foreign_key__nested_relations(graphql_client):
    postal_code_1 = PostalCodeFactory.create(code="00001")
    postal_code_2 = PostalCodeFactory.create(code="00002")
    developer_1 = DeveloperFactory.create(name="foo")

    HousingCompanyFactory.create(name="fizz", developers=[developer_1], postal_code=postal_code_1)
    HousingCompanyFactory.create(name="buzz", developers=[developer_1], postal_code=postal_code_2)

    TagFactory.create(tag="1", content_object=postal_code_1)
    TagFactory.create(tag="2", content_object=postal_code_1)
    TagFactory.create(tag="3", content_object=postal_code_1)
    TagFactory.create(tag="4", content_object=postal_code_2)
    TagFactory.create(tag="5", content_object=developer_1)
    TagFactory.create(tag="6", content_object=developer_1)

    query = """
        query {
          allTags {
            contentObject {
              ... on PostalCodeType {
                code
                housingCompanies {
                  name
                }
              }
              ... on DeveloperType {
                name
                housingcompanySet {
                  name
                }
              }
            }
          }
        }
    """

    response = graphql_client(query)
    assert response.no_errors, response.errors

    assert response.queries.count == 5, response.queries.log

    assert response.queries[0] == has(
        'FROM "example_tag"',
    )
    assert response.queries[1] == has(
        'FROM "example_postalcode"',
    )
    assert response.queries[2] == has(
        'FROM "example_developer"',
    )
    assert response.queries[3] == has(
        'FROM "example_housingcompany"',
    )
    assert response.queries[4] == has(
        'FROM "example_housingcompany"',
    )

    assert response.content == [
        {"contentObject": {"code": "00001", "housingCompanies": [{"name": "fizz"}]}},
        {"contentObject": {"code": "00001", "housingCompanies": [{"name": "fizz"}]}},
        {"contentObject": {"code": "00001", "housingCompanies": [{"name": "fizz"}]}},
        {"contentObject": {"code": "00002", "housingCompanies": [{"name": "buzz"}]}},
        {"contentObject": {"name": "foo", "housingcompanySet": [{"name": "fizz"}, {"name": "buzz"}]}},
        {"contentObject": {"name": "foo", "housingcompanySet": [{"name": "fizz"}, {"name": "buzz"}]}},
    ]


def test_same_relation_multiple_times(graphql_client):
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
            sales {
              purchaseDate
              ownerships {
                percentage
                owner {
                  name
                }
              }
            }
            sales {
              purchasePrice
              apartment {
                sharesStart
                sharesEnd
              }
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
        'FROM "example_apartment"',
    )
    assert response.queries[1] == has(
        "purchase_date",
        "purchase_price",
        'FROM "example_sale"',
        'INNER JOIN "example_apartment"',
    )
    assert response.queries[2] == has(
        'FROM "example_ownership"',
        'INNER JOIN "example_owner"',
    )
