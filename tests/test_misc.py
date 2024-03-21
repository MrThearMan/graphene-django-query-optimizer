import pytest

from tests.factories import ApartmentFactory
from tests.helpers import has

pytestmark = pytest.mark.django_db


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


def test_misc__generic_relations(graphql_client):
    query = """
        query {
          allTaggedItems {
            tag
            contentType {
              appLabel
            }
          }
        }
    """

    response = graphql_client(query)
    assert response.no_errors, response.errors

    assert response.queries.count == 1, response.queries.log
