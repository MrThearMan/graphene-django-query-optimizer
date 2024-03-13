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


def test_optimizer__annotated_field(client_query):
    query = """
        query {
          allHousingCompanies {
            greeting
          }
        }
    """

    with capture_database_queries() as results:
        response = client_query(query)

    content = json.loads(response.content)
    assert "errors" not in content, content["errors"]

    queries = len(results.queries)
    # 1 query for fetching HousingCompanies
    assert queries == 1, results.log
    assert content["data"]["allHousingCompanies"][0]["greeting"].startswith("Hello")


def test_optimizer__annotated_field__annotation_needs_joins(client_query):
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


def test_optimizer__annotated_field__in_relations(client_query):
    query = """
        query {
          allDevelopers {
            housingcompanySet {
              greeting
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
    # 1 query for fetching HousingCompanies with custom fields
    assert queries == 2, results.log


def test_optimizer__annotated_field__select_related_promoted_to_prefetch(client_query):
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


def test_optimizer__alternate_field__related_field(client_query):
    query = """
        query {
          pagedHousingCompanies {
            edges {
              node {
                name
                propertyManagerAlt {
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
    # 1 query for counting HousingCompanies
    # 1 query for fetching HousingCompanies with PropertyManagers
    assert queries == 2, results.log


def test_optimizer__alternate_field__list_field(client_query):
    query = """
        query {
          pagedHousingCompanies {
            edges {
              node {
                name
                developersAlt {
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
    # 1 query for counting HousingCompanies
    # 1 query for fetching HousingCompanies
    # 1 query for fetching nested Developers (to the alternate field)
    assert queries == 3, results.log


def test_optimizer__alternate_field__connection(client_query):
    query = """
        query {
          pagedPropertyManagers {
            edges {
              node {
                name
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

    with capture_database_queries() as results:
        response = client_query(query)

    content = json.loads(response.content)
    assert "errors" not in content, content["errors"]

    queries = len(results.queries)
    # 1 query for counting PropertyManagers
    # 1 query for fetching PropertyManagers
    # 1 query for fetching nested HousingCompanies (to the alternate field)
    assert queries == 3, results.log


def test_optimizer__alternate_field__one_to_many(client_query):
    query = """
        query {
          pagedHousingCompanies {
            edges {
              node {
                name
                realEstatesAlt {
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
    # 1 query for counting HousingCompanies
    # 1 query for fetching HousingCompanies
    # 1 query for fetching nested RealEstates (to the alternate field)
    assert queries == 3, results.log
