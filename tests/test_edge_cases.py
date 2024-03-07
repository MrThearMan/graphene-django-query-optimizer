import json

import pytest

from tests.example.utils import capture_database_queries

pytestmark = pytest.mark.django_db


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

    queries = len(results.queries)
    # 1 query for fetching Apartments and related Buildings and RealEstates
    # 1 query for fetching RealEstates and related HousingCompanies
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

    message = content["errors"][0]["message"]
    assert message == "Query complexity exceeds the maximum allowed of 10"

    queries = len(results.queries)
    # No queries since fetching is stopped due to complexity
    assert queries == 0, results.log


def test_optimizer__pk_fields(client_query):
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


def test_optimizer__named_relation(client_query):
    query = """
        query {
          examples {
            customRelation
          }
        }
    """

    with capture_database_queries() as results:
        response = client_query(query)

    content = json.loads(response.content)
    assert "errors" not in content, content["errors"]
    assert "data" in content, content

    # 1 query for all examples
    # 1 query for fetching the named relations on each example
    assert results.query_count == 1, results.log


def test_optimizer__required_fields(client_query):
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

    queries = len(results.queries)
    # 1 query for fetching HousingCompanies
    # 1 query for fetching primary RealEstate
    assert queries == 2, results.log


def test_optimizer__required_fields__in_relations(client_query):
    query = """
        query {
          allDevelopers {
            housingcompanySet {
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

    queries = len(results.queries)
    # 1 query for fetching Developers
    # 1 query for fetching HousingCompanies with custom attributes
    assert queries == 2, results.log


def test_optimizer__required_fields__backtracking(client_query):
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

    queries = len(results.queries)
    # 1 query for fetching RealEstates and related HousingCompanies
    # 1 query for fetching primary RealEstate
    assert queries == 2, results.log
