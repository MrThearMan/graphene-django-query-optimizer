import pytest
from graphql_relay import offset_to_cursor

from example_project.app.schema import Query
from example_project.app.types import DeveloperNode
from tests.factories import (
    ApartmentFactory,
    DeveloperFactory,
    EmployeeFactory,
    HousingCompanyFactory,
    PropertyManagerFactory,
    RealEstateFactory,
    TagFactory,
)
from tests.helpers import has, like

pytestmark = [
    pytest.mark.django_db,
]


def test_relay__connection(graphql_client):
    ApartmentFactory.create(street_address="1")
    ApartmentFactory.create(street_address="2")
    ApartmentFactory.create(street_address="3")

    query = """
        query {
          pagedApartments {
            edges {
              node {
                streetAddress
              }
            }
          }
        }
    """

    response = graphql_client(query)
    assert response.no_errors, response.errors

    # 1 query for counting apartments.
    # 1 query for fetching apartments.
    assert response.queries.count == 2, response.queries.log

    assert response.queries[0] == has(
        "COUNT(*)",
        'FROM "app_apartment"',
    )
    assert response.queries[1] == has(
        'FROM "app_apartment"',
        "LIMIT 3",
    )

    assert response.content == {
        "edges": [
            {"node": {"streetAddress": "1"}},
            {"node": {"streetAddress": "2"}},
            {"node": {"streetAddress": "3"}},
        ]
    }


def test_relay__connection__deep(graphql_client):
    ApartmentFactory.create(sales__ownerships__owner__name="1")
    ApartmentFactory.create(sales__ownerships__owner__name="2")
    ApartmentFactory.create(sales__ownerships__owner__name="3")

    query = """
        query {
          pagedApartments {
            edges {
              node {
                sales {
                  ownerships {
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

    response = graphql_client(query)
    assert response.no_errors, response.errors

    # 1 query for counting apartments.
    # 1 query for fetching apartments.
    # 1 query for fetching sales.
    # 1 query for fetching ownerships and related owners.
    assert response.queries.count == 4, response.queries.log

    assert response.queries[0] == has(
        "COUNT(*)",
        'FROM "app_apartment"',
    )
    assert response.queries[1] == has(
        'FROM "app_apartment"',
        "LIMIT 3",
    )
    assert response.queries[2] == has(
        'FROM "app_sale"',
    )
    assert response.queries[3] == has(
        'FROM "app_ownership"',
        'INNER JOIN "app_owner"',
    )

    assert response.content == {
        "edges": [
            {"node": {"sales": [{"ownerships": [{"owner": {"name": "1"}}]}]}},
            {"node": {"sales": [{"ownerships": [{"owner": {"name": "2"}}]}]}},
            {"node": {"sales": [{"ownerships": [{"owner": {"name": "3"}}]}]}},
        ]
    }


def test_relay__connection__only_counts(graphql_client):
    ApartmentFactory.create_batch(120)

    query = """
        query {
          pagedApartments {
            edgeCount
            totalCount
          }
        }
    """

    response = graphql_client(query)
    assert response.no_errors, response.errors

    # 1 query for counting apartments.
    # 1 query for fetching apartments (still made even if nothing is returned from it).
    assert response.queries.count == 2, response.queries.log

    assert response.queries[0] == has(
        "COUNT(*)",
        'FROM "app_apartment"',
    )
    assert response.queries[1] == has(
        'FROM "app_apartment"',
        "LIMIT 100",
    )

    assert response.content["edgeCount"] == 100
    assert response.content["totalCount"] == 120


def test_relay__connection__only_counts__filter(graphql_client):
    ApartmentFactory.create(street_address="1")
    ApartmentFactory.create(street_address="2")
    ApartmentFactory.create(street_address="3")

    query = """
        query {
          pagedApartments(streetAddress: "1") {
            edgeCount
            totalCount
          }
        }
    """

    response = graphql_client(query)
    assert response.no_errors, response.errors

    # 1 query for counting apartments.
    # 1 query for fetching apartments (still made even if nothing is returned from it).
    assert response.queries.count == 2, response.queries.log

    assert response.queries[0] == has(
        "COUNT(*)",
        'FROM "app_apartment"',
    )
    assert response.queries[1] == has(
        'FROM "app_apartment"',
        "LIMIT 1",
    )

    assert response.content["totalCount"] == 1
    assert response.content["edgeCount"] == 1


def test_relay__connection__only_cursor(graphql_client):
    ApartmentFactory.create_batch(3)

    query = """
        query {
          pagedApartments {
            edges {
              cursor
            }
          }
        }
    """

    response = graphql_client(query)
    assert response.no_errors, response.errors

    # 1 query for counting apartments.
    # 1 query for fetching apartments (still made even if nothing is returned from it).
    assert response.queries.count == 2, response.queries.log

    assert response.queries[0] == has(
        "COUNT(*)",
        'FROM "app_apartment"',
    )
    assert response.queries[1] == has(
        'FROM "app_apartment"',
        "LIMIT 3",
    )

    assert response.content == {
        "edges": [
            {"cursor": offset_to_cursor(0)},
            {"cursor": offset_to_cursor(1)},
            {"cursor": offset_to_cursor(2)},
        ]
    }


def test_relay__connection__cursor_before_node(graphql_client):
    ApartmentFactory.create(street_address="1")
    ApartmentFactory.create(street_address="2")
    ApartmentFactory.create(street_address="3")

    query = """
        query {
          pagedApartments {
            edges {
              cursor
              node {
                streetAddress
              }
            }
          }
        }
    """

    response = graphql_client(query)
    assert response.no_errors, response.errors

    # 1 query for counting apartments.
    # 1 query for fetching apartments.
    assert response.queries.count == 2, response.queries.log

    assert response.queries[0] == has(
        "COUNT(*)",
        'FROM "app_apartment"',
    )
    assert response.queries[1] == has(
        'FROM "app_apartment"',
        "LIMIT 3",
    )

    assert response.content == {
        "edges": [
            {"cursor": offset_to_cursor(0), "node": {"streetAddress": "1"}},
            {"cursor": offset_to_cursor(1), "node": {"streetAddress": "2"}},
            {"cursor": offset_to_cursor(2), "node": {"streetAddress": "3"}},
        ]
    }


def test_relay__connection__counts_before_edges(graphql_client):
    ApartmentFactory.create_batch(120)

    query = """
        query {
          pagedApartments {
            edgeCount
            totalCount
            edges {
              node {
                streetAddress
              }
            }
          }
        }
    """

    response = graphql_client(query)
    assert response.no_errors, response.errors

    # 1 query for counting apartments.
    # 1 query for fetching apartments.
    assert response.queries.count == 2, response.queries.log

    assert response.queries[0] == has(
        "COUNT(*)",
        'FROM "app_apartment"',
    )
    assert response.queries[1] == has(
        'FROM "app_apartment"',
        "LIMIT 100",
    )

    assert response.content["edgeCount"] == 100
    assert response.content["totalCount"] == 120


def test_relay__connection__more_than_max_limit(graphql_client):
    ApartmentFactory.create(street_address="1")
    ApartmentFactory.create(street_address="2")
    ApartmentFactory.create(street_address="3")
    ApartmentFactory.create(street_address="4")

    query = """
        query {
          pagedApartments {
            edges {
              node {
                streetAddress
              }
            }
          }
        }
    """

    max_limit = Query.paged_apartments.max_limit
    try:
        Query.paged_apartments.max_limit = 2
        response = graphql_client(query)
    finally:
        # Reset the limit
        Query.paged_apartments.max_limit = max_limit

    assert response.no_errors, response.errors

    assert response.content == {
        "edges": [
            {"node": {"streetAddress": "1"}},
            {"node": {"streetAddress": "2"}},
        ],
    }


def test_relay__connection__more_than_max_limit__after(graphql_client):
    ApartmentFactory.create(street_address="1")
    ApartmentFactory.create(street_address="2")
    ApartmentFactory.create(street_address="3")
    ApartmentFactory.create(street_address="4")

    query = """
        query {
          pagedApartments(after: "YXJyYXljb25uZWN0aW9uOjE=") {
            edges {
              node {
                streetAddress
              }
            }
          }
        }
    """

    max_limit = Query.paged_apartments.max_limit
    try:
        Query.paged_apartments.max_limit = 2
        response = graphql_client(query)
    finally:
        # Reset the limit
        Query.paged_apartments.max_limit = max_limit

    assert response.no_errors, response.errors

    assert response.content == {
        "edges": [
            {"node": {"streetAddress": "3"}},
            {"node": {"streetAddress": "4"}},
        ],
    }


# Nested connections


def test_relay__connection__nested__one_to_many(graphql_client):
    HousingCompanyFactory.create(real_estates__name="1")
    HousingCompanyFactory.create(real_estates__name="2")
    HousingCompanyFactory.create(real_estates__name="3")

    query = """
        query {
          pagedHousingCompanies {
            edges {
              node {
                realEstates {
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

    # 1 query to count housing companies.
    # 1 query to fetch housing companies.
    # 1 query to fetch related real estates.
    assert response.queries.count == 3, response.queries.log

    assert response.queries[0] == has(
        "COUNT(*)",
        'FROM "app_housingcompany"',
    )
    assert response.queries[1] == has(
        'FROM "app_housingcompany"',
        "LIMIT 3",
    )
    assert response.queries[2] == has(
        'FROM "app_realestate"',
        # Nested connections are limited via a window function.
        ('ROW_NUMBER() OVER (PARTITION BY "app_realestate"."housing_company_id" ORDER BY "app_realestate"."id")'),
    )

    assert response.content == {
        "edges": [
            {"node": {"realEstates": {"edges": [{"node": {"name": "1"}}]}}},
            {"node": {"realEstates": {"edges": [{"node": {"name": "2"}}]}}},
            {"node": {"realEstates": {"edges": [{"node": {"name": "3"}}]}}},
        ]
    }


def test_relay__connection__nested__many_to_many(graphql_client):
    HousingCompanyFactory.create(developers__name="1")
    HousingCompanyFactory.create(developers__name="2")
    HousingCompanyFactory.create(developers__name="3")

    query = """
        query {
          pagedHousingCompanies {
            edges {
              node {
                developers {
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

    # 1 query to count housing companies.
    # 1 query to fetch housing companies.
    # 1 query to fetch related developers.
    assert response.queries.count == 3, response.queries.log

    assert response.queries[0] == has(
        "COUNT(*)",
        'FROM "app_housingcompany"',
    )
    assert response.queries[1] == has(
        'FROM "app_housingcompany"',
        "LIMIT 3",
    )
    assert response.queries[2] == has(
        'FROM "app_developer"',
        # Nested connections are limited via a window function.
        (
            "ROW_NUMBER() OVER "
            '(PARTITION BY "app_housingcompany_developers"."housingcompany_id" ORDER BY "app_developer"."id")'
        ),
    )

    assert response.content == {
        "edges": [
            {"node": {"developers": {"edges": [{"node": {"name": "1"}}]}}},
            {"node": {"developers": {"edges": [{"node": {"name": "2"}}]}}},
            {"node": {"developers": {"edges": [{"node": {"name": "3"}}]}}},
        ]
    }


def test_relay__connection__nested__many_to_many__multiple(graphql_client):
    HousingCompanyFactory.create(developers__name="1", shareholders__name="1")
    HousingCompanyFactory.create(developers__name="2", shareholders__name="1")
    HousingCompanyFactory.create(developers__name="3", shareholders__name="1")

    query = """
        query {
          pagedHousingCompanies {
            edges {
              node {
                developers {
                  edges {
                    node {
                      name
                    }
                  }
                }
                shareholders {
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

    # 1 query to count housing companies.
    # 1 query to fetch housing companies.
    # 1 query to fetch related developers.
    # 1 query to fetch related shareholders.
    assert response.queries.count == 4, response.queries.log

    assert response.queries[0] == has(
        "COUNT(*)",
        'FROM "app_housingcompany"',
    )
    assert response.queries[1] == has(
        'FROM "app_housingcompany"',
        "LIMIT 3",
    )
    assert response.queries[2] == has(
        'FROM "app_developer"',
        # Nested connections are limited via a window function.
        (
            "ROW_NUMBER() OVER "
            '(PARTITION BY "app_housingcompany_developers"."housingcompany_id" ORDER BY "app_developer"."id")'
        ),
    )
    assert response.queries[3] == has(
        'FROM "app_shareholder"',
        # Nested connections are limited via a window function.
        'ROW_NUMBER() OVER (PARTITION BY "app_housingcompany_shareholders"."housingcompany_id")',
    )

    assert response.content == {
        "edges": [
            {
                "node": {
                    "developers": {"edges": [{"node": {"name": "1"}}]},
                    "shareholders": {"edges": [{"node": {"name": "1"}}]},
                },
            },
            {
                "node": {
                    "developers": {"edges": [{"node": {"name": "2"}}]},
                    "shareholders": {"edges": [{"node": {"name": "1"}}]},
                },
            },
            {
                "node": {
                    "developers": {"edges": [{"node": {"name": "3"}}]},
                    "shareholders": {"edges": [{"node": {"name": "1"}}]},
                },
            },
        ],
    }


def test_relay__connection__nested__many_to_many__second_level_is_generic_relation(graphql_client):
    dev_1 = DeveloperFactory.create(name="1")
    dev_2 = DeveloperFactory.create(name="2")
    dev_3 = DeveloperFactory.create(name="3")

    TagFactory.create(tag="1", content_object=dev_1)
    TagFactory.create(tag="2", content_object=dev_1)
    TagFactory.create(tag="3", content_object=dev_2)
    TagFactory.create(tag="4", content_object=dev_2)
    TagFactory.create(tag="5", content_object=dev_3)
    TagFactory.create(tag="6", content_object=dev_3)

    HousingCompanyFactory.create(developers=[dev_1, dev_2])
    HousingCompanyFactory.create(developers=[dev_2])
    HousingCompanyFactory.create(developers=[dev_3, dev_1])

    query = """
        query {
          pagedHousingCompanies {
            edges {
              node {
                developers {
                  edges {
                    node {
                      name
                      tags {
                        edges {
                          node {
                            tag
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
    assert response.no_errors, response.errors

    # 1 query to count housing companies.
    # 1 query to fetch housing companies.
    # 1 query to fetch related developers.
    # 1 query to fetch related tags.
    assert response.queries.count == 4, response.queries.log

    assert response.queries[0] == has(
        "COUNT(*)",
        'FROM "app_housingcompany"',
    )
    assert response.queries[1] == has(
        'FROM "app_housingcompany"',
        "LIMIT 3",
    )
    assert response.queries[2] == has(
        'FROM "app_developer"',
        # Nested connections are limited via a window function.
        (
            "ROW_NUMBER() OVER "
            '(PARTITION BY "app_housingcompany_developers"."housingcompany_id" ORDER BY "app_developer"."id")'
        ),
    )
    assert response.queries[3] == has(
        'FROM "app_tag"',
        # Nested connections are limited via a window function.
        'ROW_NUMBER() OVER (PARTITION BY "app_developer"."id")',
    )

    assert response.content == {
        "edges": [
            {
                "node": {
                    "developers": {
                        "edges": [
                            {
                                "node": {
                                    "name": "1",
                                    "tags": {
                                        "edges": [
                                            {"node": {"tag": "1"}},
                                            {"node": {"tag": "2"}},
                                        ],
                                    },
                                }
                            },
                            {
                                "node": {
                                    "name": "2",
                                    "tags": {
                                        "edges": [
                                            {"node": {"tag": "3"}},
                                            {"node": {"tag": "4"}},
                                        ],
                                    },
                                },
                            },
                        ],
                    },
                },
            },
            {
                "node": {
                    "developers": {
                        "edges": [
                            {
                                "node": {
                                    "name": "2",
                                    "tags": {
                                        "edges": [
                                            {"node": {"tag": "3"}},
                                            {"node": {"tag": "4"}},
                                        ],
                                    },
                                },
                            },
                        ],
                    },
                },
            },
            {
                "node": {
                    "developers": {
                        "edges": [
                            {
                                "node": {
                                    "name": "1",
                                    "tags": {
                                        "edges": [
                                            {"node": {"tag": "1"}},
                                            {"node": {"tag": "2"}},
                                        ],
                                    },
                                }
                            },
                            {
                                "node": {
                                    "name": "3",
                                    "tags": {
                                        "edges": [
                                            {"node": {"tag": "5"}},
                                            {"node": {"tag": "6"}},
                                        ],
                                    },
                                },
                            },
                        ],
                    },
                },
            },
        ],
    }


def test_relay__connection__nested__many_to_many__second_level_is_many_to_many(graphql_client):
    dev_1 = DeveloperFactory.create(name="1")
    dev_2 = DeveloperFactory.create(name="2")
    dev_3 = DeveloperFactory.create(name="3")

    EmployeeFactory.create(name="1", developers=[dev_1])
    EmployeeFactory.create(name="2", developers=[dev_1])
    EmployeeFactory.create(name="3", developers=[dev_2])
    EmployeeFactory.create(name="4", developers=[dev_2])
    EmployeeFactory.create(name="5", developers=[dev_3])
    EmployeeFactory.create(name="6", developers=[dev_3])

    HousingCompanyFactory.create(developers=[dev_1, dev_2])
    HousingCompanyFactory.create(developers=[dev_2])
    HousingCompanyFactory.create(developers=[dev_3, dev_1])

    query = """
        query {
          pagedHousingCompanies {
            edges {
              node {
                developers {
                  edges {
                    node {
                      employees {
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
    """

    response = graphql_client(query)
    assert response.no_errors, response.errors

    # 1 query to count housing companies.
    # 1 query to fetch housing companies.
    # 1 query to fetch related developers.
    # 1 query to fetch related employees.
    assert response.queries.count == 4, response.queries.log

    assert response.queries[0] == has(
        "COUNT(*)",
        'FROM "app_housingcompany"',
    )
    assert response.queries[1] == has(
        'FROM "app_housingcompany"',
        "LIMIT 3",
    )
    assert response.queries[2] == has(
        'FROM "app_developer"',
        # Nested connections are limited via a window function.
        (
            "ROW_NUMBER() OVER "
            '(PARTITION BY "app_housingcompany_developers"."housingcompany_id" ORDER BY "app_developer"."id")'
        ),
    )
    assert response.queries[3] == has(
        'FROM "app_employee"',
        # Nested connections are limited via a window function.
        'ROW_NUMBER() OVER (PARTITION BY "app_developer_employees"."developer_id")',
    )

    assert response.content == {
        "edges": [
            {
                "node": {
                    "developers": {
                        "edges": [
                            {
                                "node": {
                                    "employees": {
                                        "edges": [
                                            {"node": {"name": "1"}},
                                            {"node": {"name": "2"}},
                                        ],
                                    },
                                },
                            },
                            {
                                "node": {
                                    "employees": {
                                        "edges": [
                                            {"node": {"name": "3"}},
                                            {"node": {"name": "4"}},
                                        ],
                                    },
                                },
                            },
                        ],
                    },
                },
            },
            {
                "node": {
                    "developers": {
                        "edges": [
                            {
                                "node": {
                                    "employees": {
                                        "edges": [
                                            {"node": {"name": "3"}},
                                            {"node": {"name": "4"}},
                                        ],
                                    },
                                },
                            },
                        ],
                    },
                },
            },
            {
                "node": {
                    "developers": {
                        "edges": [
                            {
                                "node": {
                                    "employees": {
                                        "edges": [
                                            {"node": {"name": "1"}},
                                            {"node": {"name": "2"}},
                                        ],
                                    },
                                },
                            },
                            {
                                "node": {
                                    "employees": {
                                        "edges": [
                                            {"node": {"name": "5"}},
                                            {"node": {"name": "6"}},
                                        ],
                                    },
                                },
                            },
                        ],
                    },
                },
            },
        ],
    }


def test_relay__connection__nested__many_to_many__reverse(graphql_client):
    DeveloperFactory.create(housingcompany_set__name="1")
    DeveloperFactory.create(housingcompany_set__name="2")
    DeveloperFactory.create(housingcompany_set__name="3")

    query = """
        query {
          pagedDevelopers {
            edges {
              node {
                housingcompanySet {
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

    # 1 query for counting developers.
    # 1 query for fetching developers.
    # 1 query for fetching housing companies.
    assert response.queries.count == 3, response.queries.log

    assert response.queries[0] == has(
        "COUNT(*)",
        'FROM "app_developer"',
    )
    assert response.queries[1] == has(
        'FROM "app_developer"',
        "LIMIT 3",
    )
    assert response.queries[2] == has(
        'FROM "app_housingcompany"',
        # Nested connections are limited via a window function.
        (
            "ROW_NUMBER() OVER "
            '(PARTITION BY "app_housingcompany_developers"."developer_id" ORDER BY "app_housingcompany"."id")'
        ),
    )

    assert response.content == {
        "edges": [
            {"node": {"housingcompanySet": {"edges": [{"node": {"name": "1"}}]}}},
            {"node": {"housingcompanySet": {"edges": [{"node": {"name": "2"}}]}}},
            {"node": {"housingcompanySet": {"edges": [{"node": {"name": "3"}}]}}},
        ]
    }


def test_relay__connection__nested__no_related_name(graphql_client):
    RealEstateFactory.create(building_set__name="1")
    RealEstateFactory.create(building_set__name="2")
    RealEstateFactory.create(building_set__name="3")

    query = """
        query {
          pagedRealEstates {
            edges {
              node {
                buildingSet {
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

    # 1 query to count real estates.
    # 1 query to fetch real estates.
    # 1 query to fetch related buildings.
    assert response.queries.count == 3, response.queries.log

    assert response.queries[0] == has(
        "COUNT(*)",
        'FROM "app_realestate"',
    )
    assert response.queries[1] == has(
        'FROM "app_realestate"',
        "LIMIT 3",
    )
    assert response.queries[2] == has(
        'FROM "app_building"',
        # Nested connections are limited via a window function.
        'ROW_NUMBER() OVER (PARTITION BY "app_building"."real_estate_id" ORDER BY "app_building"."id")',
    )

    assert response.content == {
        "edges": [
            {"node": {"buildingSet": {"edges": [{"node": {"name": "1"}}]}}},
            {"node": {"buildingSet": {"edges": [{"node": {"name": "2"}}]}}},
            {"node": {"buildingSet": {"edges": [{"node": {"name": "3"}}]}}},
        ]
    }


def test_relay__connection__nested__many_to_many__shared_entities(graphql_client):
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
          pagedHousingCompanies {
            edges {
              node {
                developers {
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

    # 1 query to count housing companies.
    # 1 query to fetch housing companies.
    # 1 query to fetch related real estates.
    assert response.queries.count == 3, response.queries.log

    assert response.queries[0] == has(
        "COUNT(*)",
        'FROM "app_housingcompany"',
    )
    assert response.queries[1] == has(
        'FROM "app_housingcompany"',
        "LIMIT 3",
    )
    assert response.queries[2] == has(
        'FROM "app_developer"',
        # Nested connections are limited via a window function.
        (
            "ROW_NUMBER() OVER "
            '(PARTITION BY "app_housingcompany_developers"."housingcompany_id" ORDER BY "app_developer"."id")'
        ),
    )

    assert response.content == {
        "edges": [
            {
                "node": {
                    "developers": {
                        "edges": [
                            {"node": {"name": "1"}},
                            {"node": {"name": "2"}},
                            {"node": {"name": "3"}},
                        ],
                    },
                },
            },
            {
                "node": {
                    "developers": {
                        "edges": [
                            {"node": {"name": "3"}},
                            {"node": {"name": "5"}},
                            {"node": {"name": "6"}},
                        ],
                    },
                },
            },
            {
                "node": {
                    "developers": {
                        "edges": [
                            {"node": {"name": "1"}},
                            {"node": {"name": "3"}},
                            {"node": {"name": "4"}},
                            {"node": {"name": "6"}},
                        ],
                    },
                },
            },
        ],
    }


def test_relay__connection__nested__counts(graphql_client):
    PropertyManagerFactory.create(housing_companies__name="1")
    PropertyManagerFactory.create(housing_companies__name="2")
    PropertyManagerFactory.create(housing_companies__name="3")

    query = """
        query {
          pagedPropertyManagers {
            edges {
              node {
                housingCompanies {
                  edgeCount
                  totalCount
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

    # 1 query for counting property managers.
    # 1 query for fetching property managers.
    # 1 query for fetching housing companies (and counting them in a subquery).
    assert response.queries.count == 3, response.queries.log

    assert response.queries[0] == has(
        "COUNT(*)",
        'FROM "app_propertymanager"',
    )

    assert response.queries[1] == has(
        'FROM "app_propertymanager"',
        "LIMIT 3",
    )

    assert response.queries[2] == has(
        'FROM "app_housingcompany"',
        (
            "ROW_NUMBER() OVER "
            '(PARTITION BY "app_housingcompany"."property_manager_id" ORDER BY "app_housingcompany"."id")'
        ),
    )

    # Check that total count is calculated if selected in the query.
    assert response.queries[2] == like(
        r'.*\(SELECT COUNT\(\*\) FROM \(SELECT .* FROM "app_housingcompany" .*\) _count\) AS "_optimizer_count".*'
    )


def test_relay__connection__nested__no_counts(graphql_client):
    PropertyManagerFactory.create(housing_companies__name="1")
    PropertyManagerFactory.create(housing_companies__name="2")
    PropertyManagerFactory.create(housing_companies__name="3")

    query = """
        query {
          pagedPropertyManagers {
            edges {
              node {
                housingCompanies {
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

    # 1 query for counting property managers.
    # 1 query for fetching property managers.
    # 1 query for fetching housing companies (and counting them in a subquery).
    assert response.queries.count == 3, response.queries.log

    # Check that total count is not calculated if not selected in the query.
    assert response.queries[2] != like(
        r'.*\(SELECT COUNT\(\*\) FROM \(SELECT .* FROM "app_housingcompany" .*\) _count\) AS "_optimizer_count".*'
    )


def test_relay__connection__nested__more_than_max_limit(graphql_client):
    developer_1 = DeveloperFactory.create()
    HousingCompanyFactory.create(name="1", developers=[developer_1])
    HousingCompanyFactory.create(name="2", developers=[developer_1])
    HousingCompanyFactory.create(name="3", developers=[developer_1])
    HousingCompanyFactory.create(name="4", developers=[developer_1])

    developer_2 = DeveloperFactory.create()
    HousingCompanyFactory.create(name="5", developers=[developer_2])
    HousingCompanyFactory.create(name="6", developers=[developer_2])
    HousingCompanyFactory.create(name="7", developers=[developer_2])

    query = """
        query {
          pagedDevelopers {
            edges {
              node {
                housingcompanySet {
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

    max_limit = DeveloperNode.housingcompany_set.max_limit
    try:
        DeveloperNode.housingcompany_set.max_limit = 2
        response = graphql_client(query)
    finally:
        # Reset the limit
        DeveloperNode.housingcompany_set.max_limit = max_limit

    assert response.no_errors, response.errors

    assert response.content == {
        "edges": [
            {
                "node": {
                    "housingcompanySet": {
                        "edges": [
                            {"node": {"name": "1"}},
                            {"node": {"name": "2"}},
                        ]
                    }
                }
            },
            {
                "node": {
                    "housingcompanySet": {
                        "edges": [
                            {"node": {"name": "5"}},
                            {"node": {"name": "6"}},
                        ],
                    },
                },
            },
        ]
    }


def test_relay__connection__nested__more_than_max_limit__after(graphql_client):
    developer_1 = DeveloperFactory.create()
    HousingCompanyFactory.create(name="1", developers=[developer_1])
    HousingCompanyFactory.create(name="2", developers=[developer_1])
    HousingCompanyFactory.create(name="3", developers=[developer_1])
    HousingCompanyFactory.create(name="4", developers=[developer_1])

    developer_2 = DeveloperFactory.create()
    HousingCompanyFactory.create(name="5", developers=[developer_2])
    HousingCompanyFactory.create(name="6", developers=[developer_2])
    HousingCompanyFactory.create(name="7", developers=[developer_2])

    query = """
        query {
          pagedDevelopers {
            edges {
              node {
                housingcompanySet(after: "YXJyYXljb25uZWN0aW9uOjE=") {
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

    max_limit = DeveloperNode.housingcompany_set.max_limit
    try:
        DeveloperNode.housingcompany_set.max_limit = 2
        response = graphql_client(query)
    finally:
        # Reset the limit
        DeveloperNode.housingcompany_set.max_limit = max_limit

    assert response.no_errors, response.errors

    assert response.content == {
        "edges": [
            {
                "node": {
                    "housingcompanySet": {
                        "edges": [
                            {"node": {"name": "3"}},
                            {"node": {"name": "4"}},
                        ]
                    }
                }
            },
            {
                "node": {
                    "housingcompanySet": {
                        "edges": [
                            {"node": {"name": "7"}},
                        ],
                    },
                },
            },
        ]
    }
