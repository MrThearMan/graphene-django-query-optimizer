import pytest

from tests.factories import (
    ApartmentFactory,
    BuildingFactory,
    DeveloperFactory,
    HousingCompanyFactory,
    PropertyManagerFactory,
    RealEstateFactory,
)
from tests.helpers import has

pytestmark = [
    pytest.mark.django_db,
]


def test_filter__to_one_relation(graphql_client):
    HousingCompanyFactory.create(name="1", postal_code__code="00001")
    HousingCompanyFactory.create(name="2", postal_code__code="00002")
    HousingCompanyFactory.create(name="3", postal_code__code="00003")

    query = """
        query {
          pagedHousingCompanies(postalCode_Code_Iexact: "00001") {
            edges {
              node {
                name
              }
            }
          }
        }
    """

    response = graphql_client(query)
    assert response.no_errors, response.errors

    # 1 query for counting housing companies.
    # 1 query for fetching housing companies.
    assert response.queries.count == 2, response.queries.log

    assert response.queries[0] == has(
        "COUNT(*)",
        'FROM "app_housingcompany"',
    )
    assert response.queries[1] == has(
        'FROM "app_housingcompany"',
    )

    assert response.content == {
        "edges": [
            {"node": {"name": "1"}},
        ],
    }


def test_filter__to_many_relation(graphql_client):
    HousingCompanyFactory.create(name="1", developers__name="1")
    HousingCompanyFactory.create(name="2", developers__name="2")
    HousingCompanyFactory.create(name="3", developers__name="3")

    query = """
        query {
          pagedHousingCompanies(developers_Name_Iexact: "1") {
            edges {
              node {
                name
              }
            }
          }
        }
    """

    response = graphql_client(query)
    assert response.no_errors, response.errors

    # 1 query for counting housing companies.
    # 1 query for fetching housing companies.
    assert response.queries.count == 2, response.queries.log

    assert response.queries[0] == has(
        "COUNT(*)",
        'FROM "app_housingcompany"',
    )
    assert response.queries[1] == has(
        'FROM "app_housingcompany"',
    )

    assert response.content == {
        "edges": [
            {"node": {"name": "1"}},
        ],
    }


def test_filter__custom_filter(graphql_client):
    HousingCompanyFactory.create(name="1", street_address="Example", postal_code__code="00001", city="Helsinki")
    HousingCompanyFactory.create(name="2", street_address="Other", postal_code__code="00002", city="London")
    HousingCompanyFactory.create(name="3", street_address="Thing", postal_code__code="00003", city="Paris")

    query = """
        query {
          pagedHousingCompanies(address: "00001") {
            edges {
              node {
                name
              }
            }
          }
        }
    """

    response = graphql_client(query)
    assert response.no_errors, response.errors

    # 1 query for counting housing companies.
    # 1 query for fetching housing companies.
    assert response.queries.count == 2, response.queries.log

    assert response.queries[0] == has(
        "COUNT(*)",
        'FROM "app_housingcompany"',
    )
    assert response.queries[1] == has(
        'FROM "app_housingcompany"',
    )

    assert response.content == {
        "edges": [
            {"node": {"name": "1"}},
        ],
    }


def test_filter__order_by(graphql_client):
    HousingCompanyFactory.create(name="1")
    HousingCompanyFactory.create(name="3")
    HousingCompanyFactory.create(name="2")

    query = """
        query {
          pagedHousingCompanies(orderBy: "name") {
            edges {
              node {
                name
              }
            }
          }
        }
    """

    response = graphql_client(query)
    assert response.no_errors, response.errors

    # 1 query for counting housing companies.
    # 1 query for fetching housing companies.
    assert response.queries.count == 2, response.queries.log

    assert response.queries[0] == has(
        "COUNT(*)",
        'FROM "app_housingcompany"',
    )
    assert response.queries[1] == has(
        'FROM "app_housingcompany"',
    )

    assert response.content == {
        "edges": [
            {"node": {"name": "1"}},
            {"node": {"name": "2"}},
            {"node": {"name": "3"}},
        ],
    }


def test_filter__order_by__multiple(graphql_client):
    HousingCompanyFactory.create(name="1", street_address="1")
    HousingCompanyFactory.create(name="3", street_address="1")
    HousingCompanyFactory.create(name="2", street_address="1")

    query = """
        query {
          pagedHousingCompanies(orderBy: "street_address,name") {
            edges {
              node {
                name
              }
            }
          }
        }
    """

    response = graphql_client(query)
    assert response.no_errors, response.errors

    # 1 query for counting housing companies.
    # 1 query for fetching housing companies.
    assert response.queries.count == 2, response.queries.log

    assert response.queries[0] == has(
        "COUNT(*)",
        'FROM "app_housingcompany"',
    )
    assert response.queries[1] == has(
        'FROM "app_housingcompany"',
    )

    assert response.content == {
        "edges": [
            {"node": {"name": "1"}},
            {"node": {"name": "2"}},
            {"node": {"name": "3"}},
        ],
    }


def test_filter__order_by__camelcase_asc(graphql_client):
    HousingCompanyFactory.create(name="1", street_address="1")
    HousingCompanyFactory.create(name="2", street_address="2")

    query = """
        query {
          pagedHousingCompanies(orderBy: "streetAddress") {
            edges {
              node {
                name
                streetAddress
              }
            }
          }
        }
    """
    response = graphql_client(query)
    assert response.no_errors, response.errors

    assert response.content == {
        "edges": [
            {
                "node": {
                    "name": "1",
                    "streetAddress": "1",
                }
            },
            {
                "node": {
                    "name": "2",
                    "streetAddress": "2",
                }
            },
        ]
    }


def test_filter__order_by__camelcase_desc(graphql_client):
    HousingCompanyFactory.create(name="1", street_address="1")
    HousingCompanyFactory.create(name="2", street_address="2")

    query = """
        query {
          pagedHousingCompanies(orderBy: "-streetAddress") {
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

    assert response.content == {
        "edges": [
            {
                "node": {
                    "streetAddress": "2",
                }
            },
            {
                "node": {
                    "streetAddress": "1",
                }
            },
        ]
    }


def test_filter__order_by__nested__asc(graphql_client):
    developer_1 = DeveloperFactory.create(name="1")
    developer_2 = DeveloperFactory.create(name="3")
    developer_3 = DeveloperFactory.create(name="2")
    HousingCompanyFactory.create(name="1", developers=[developer_1, developer_2])
    HousingCompanyFactory.create(name="2", developers=[developer_3, developer_2])
    HousingCompanyFactory.create(name="3", developers=[developer_1, developer_3])

    query = """
        query {
          pagedDevelopers {
            edges {
              node {
                name
                housingcompanySet(orderBy: "name") {
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
    # 1 query for fetching housing companies.
    # 1 query for fetching housing companies.
    assert response.queries.count == 3, response.queries.log

    assert response.queries[0] == has(
        "COUNT(*)",
        'FROM "app_developer"',
    )
    assert response.queries[1] == has(
        'FROM "app_developer"',
    )
    assert response.queries[2] == has(
        'FROM "app_housingcompany"',
    )

    assert response.content == {
        "edges": [
            {
                "node": {
                    "name": "1",
                    "housingcompanySet": {
                        "edges": [
                            {"node": {"name": "1"}},
                            {"node": {"name": "3"}},
                        ],
                    },
                }
            },
            {
                "node": {
                    "name": "3",
                    "housingcompanySet": {
                        "edges": [
                            {"node": {"name": "1"}},
                            {"node": {"name": "2"}},
                        ],
                    },
                }
            },
            {
                "node": {
                    "name": "2",
                    "housingcompanySet": {
                        "edges": [
                            {"node": {"name": "2"}},
                            {"node": {"name": "3"}},
                        ],
                    },
                }
            },
        ]
    }


def test_filter__order_by__nested__desc(graphql_client):
    developer_1 = DeveloperFactory.create(name="1")
    developer_2 = DeveloperFactory.create(name="3")
    developer_3 = DeveloperFactory.create(name="2")
    HousingCompanyFactory.create(name="1", developers=[developer_1, developer_2])
    HousingCompanyFactory.create(name="2", developers=[developer_3, developer_2])
    HousingCompanyFactory.create(name="3", developers=[developer_1, developer_3])

    query = """
        query {
          pagedDevelopers {
            edges {
              node {
                name
                housingcompanySet(orderBy: "-name") {
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
    # 1 query for fetching housing companies.
    # 1 query for fetching housing companies.
    assert response.queries.count == 3, response.queries.log

    assert response.queries[0] == has(
        "COUNT(*)",
        'FROM "app_developer"',
    )
    assert response.queries[1] == has(
        'FROM "app_developer"',
    )
    assert response.queries[2] == has(
        'FROM "app_housingcompany"',
    )

    assert response.content == {
        "edges": [
            {
                "node": {
                    "name": "1",
                    "housingcompanySet": {
                        "edges": [
                            {"node": {"name": "3"}},
                            {"node": {"name": "1"}},
                        ],
                    },
                }
            },
            {
                "node": {
                    "name": "3",
                    "housingcompanySet": {
                        "edges": [
                            {"node": {"name": "2"}},
                            {"node": {"name": "1"}},
                        ],
                    },
                }
            },
            {
                "node": {
                    "name": "2",
                    "housingcompanySet": {
                        "edges": [
                            {"node": {"name": "3"}},
                            {"node": {"name": "2"}},
                        ],
                    },
                }
            },
        ]
    }


def test_filter__order_by__nested__multiple(graphql_client):
    developer_1 = DeveloperFactory.create(name="1")
    developer_2 = DeveloperFactory.create(name="3")
    developer_3 = DeveloperFactory.create(name="2")
    HousingCompanyFactory.create(name="1", developers=[developer_1, developer_2])
    HousingCompanyFactory.create(name="2", developers=[developer_3, developer_2])
    HousingCompanyFactory.create(name="3", developers=[developer_1, developer_3])

    query = """
        query {
          pagedDevelopers {
            edges {
              node {
                name
                housingcompanySet(orderBy: "name,street_address") {
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
    # 1 query for fetching housing companies.
    # 1 query for fetching housing companies.
    assert response.queries.count == 3, response.queries.log

    assert response.queries[0] == has(
        "COUNT(*)",
        'FROM "app_developer"',
    )
    assert response.queries[1] == has(
        'FROM "app_developer"',
    )
    assert response.queries[2] == has(
        'FROM "app_housingcompany"',
    )

    assert response.content == {
        "edges": [
            {
                "node": {
                    "name": "1",
                    "housingcompanySet": {
                        "edges": [
                            {"node": {"name": "1"}},
                            {"node": {"name": "3"}},
                        ],
                    },
                }
            },
            {
                "node": {
                    "name": "3",
                    "housingcompanySet": {
                        "edges": [
                            {"node": {"name": "1"}},
                            {"node": {"name": "2"}},
                        ],
                    },
                }
            },
            {
                "node": {
                    "name": "2",
                    "housingcompanySet": {
                        "edges": [
                            {"node": {"name": "2"}},
                            {"node": {"name": "3"}},
                        ],
                    },
                }
            },
        ]
    }


def test_filter__order_by__camelcase__nested_asc(graphql_client):
    developer_1 = DeveloperFactory.create(name="1")
    HousingCompanyFactory.create(name="1", street_address="1", developers=[developer_1])
    HousingCompanyFactory.create(name="2", street_address="2", developers=[developer_1])

    query = """
        query {
          pagedDevelopers {
            edges {
              node {
                name
                housingcompanySet(orderBy: "streetAddress") {
                  edges {
                    node {
                      streetAddress
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

    assert response.content == {
        "edges": [
            {
                "node": {
                    "name": "1",
                    "housingcompanySet": {
                        "edges": [
                            {"node": {"streetAddress": "1"}},
                            {"node": {"streetAddress": "2"}},
                        ],
                    },
                }
            },
        ]
    }


def test_filter__order_by__camelcase__nested_desc(graphql_client):
    developer_1 = DeveloperFactory.create(name="1")
    HousingCompanyFactory.create(name="1", street_address="1", developers=[developer_1])
    HousingCompanyFactory.create(name="2", street_address="2", developers=[developer_1])

    query = """
        query {
          pagedDevelopers {
            edges {
              node {
                name
                housingcompanySet(orderBy: "-streetAddress") {
                  edges {
                    node {
                      streetAddress
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

    assert response.content == {
        "edges": [
            {
                "node": {
                    "name": "1",
                    "housingcompanySet": {
                        "edges": [
                            {"node": {"streetAddress": "2"}},
                            {"node": {"streetAddress": "1"}},
                        ],
                    },
                }
            },
        ]
    }


def test_filter__list_field(graphql_client):
    ApartmentFactory.create(street_address="1")
    ApartmentFactory.create(street_address="2")
    ApartmentFactory.create(street_address="3")

    query = """
        query {
          allApartments(streetAddress:"1") {
            streetAddress
          }
        }
    """

    response = graphql_client(query)
    assert response.no_errors, response.errors

    # 1 query for fetching apartments.
    assert response.queries.count == 1, response.queries.log

    assert response.queries[0] == has(
        'FROM "app_apartment"',
    )

    assert response.content == [{"streetAddress": "1"}]


def test_filter__nested_list_field(graphql_client):
    BuildingFactory.create(name="1", apartments__street_address="1")
    BuildingFactory.create(name="2", apartments__street_address="2")
    BuildingFactory.create(name="3", apartments__street_address="3")

    query = """
        query {
          allBuildings {
            apartments(streetAddress:"1") {
              streetAddress
            }
          }
        }
    """

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

    assert response.content == [
        {
            "apartments": [{"streetAddress": "1"}],
        },
        {
            "apartments": [],
        },
        {
            "apartments": [],
        },
    ]


def test_filter__nested_connection(graphql_client):
    PropertyManagerFactory.create(housing_companies__name="1")
    PropertyManagerFactory.create(housing_companies__name="2")
    PropertyManagerFactory.create(housing_companies__name="3")

    query = """
        query {
          pagedPropertyManagers {
            edges {
              node {
                housingCompanies(name_Iexact: "1") {
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
    # 1 query for fetching related housing companies.
    assert response.queries.count == 3, response.queries.log

    assert response.queries[0] == has(
        "COUNT(*)",
        'FROM "app_propertymanager"',
    )
    assert response.queries[1] == has(
        'FROM "app_propertymanager"',
        "LIMIT 3",
    )
    # Check that the filter is actually applied
    assert response.queries[2] == has(
        'FROM "app_housingcompany"',
        (
            "ROW_NUMBER() OVER "
            '(PARTITION BY "app_housingcompany"."property_manager_id" ORDER BY "app_housingcompany"."id")'
        ),
    )

    assert response.content == {
        "edges": [
            {"node": {"housingCompanies": {"edges": [{"node": {"name": "1"}}]}}},
            {"node": {"housingCompanies": {"edges": []}}},
            {"node": {"housingCompanies": {"edges": []}}},
        ]
    }


def test_filter__nested_connection__deep(graphql_client):
    PropertyManagerFactory.create(housing_companies__real_estates__name="1")
    PropertyManagerFactory.create(housing_companies__real_estates__name="2")
    PropertyManagerFactory.create(housing_companies__real_estates__name="3")

    query = """
        query {
          pagedPropertyManagers {
            edges {
              node {
                housingCompanies {
                  edges {
                    node {
                      realEstates(name:"1") {
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

    # 1 query for counting property managers.
    # 1 query for fetching property managers.
    # 1 query for fetching housing companies.
    # 1 query for fetching real estates.
    assert response.queries.count == 4, response.queries.log

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
    assert response.queries[3] == has(
        'FROM "app_realestate"',
        ('ROW_NUMBER() OVER (PARTITION BY "app_realestate"."housing_company_id" ORDER BY "app_realestate"."id")'),
    )

    assert response.content == {
        "edges": [
            {
                "node": {
                    "housingCompanies": {
                        "edges": [
                            {
                                "node": {
                                    "realEstates": {
                                        "edges": [
                                            {"node": {"name": "1"}},
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
                    "housingCompanies": {
                        "edges": [
                            {
                                "node": {
                                    "realEstates": {
                                        "edges": [],
                                    },
                                },
                            },
                        ],
                    },
                },
            },
            {
                "node": {
                    "housingCompanies": {
                        "edges": [
                            {
                                "node": {
                                    "realEstates": {
                                        "edges": [],
                                    },
                                },
                            },
                        ],
                    },
                },
            },
        ]
    }


def test_filter__nested_connection__fragment_spread(graphql_client):
    PropertyManagerFactory.create(housing_companies__name="1")
    PropertyManagerFactory.create(housing_companies__name="2")
    PropertyManagerFactory.create(housing_companies__name="3")

    query = """
        fragment Companies on PropertyManagerNode {
          housingCompanies(name_Iexact: "1") {
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
                ...Companies
              }
            }
          }
        }
    """

    response = graphql_client(query)
    assert response.no_errors, response.errors

    # 1 query for counting property managers.
    # 1 query for fetching property managers.
    # 1 query for fetching housing companies.
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

    assert response.content == {
        "edges": [
            {"node": {"housingCompanies": {"edges": [{"node": {"name": "1"}}]}}},
            {"node": {"housingCompanies": {"edges": []}}},
            {"node": {"housingCompanies": {"edges": []}}},
        ]
    }


def test_filter__invalid_value(graphql_client):
    RealEstateFactory.create(name="1", surface_area=1)
    RealEstateFactory.create(name="2", surface_area=2)
    RealEstateFactory.create(name="3", surface_area=3)

    query = """
        query {
          pagedRealEstates(surfaceArea: "foo") {
            edges {
              node {
                name
              }
            }
          }
        }
    """

    response = graphql_client(query)
    assert response.errors[0]["message"] == """Expected value of type 'Decimal', found "foo"."""


def test_filter__aliased_queries(graphql_client):
    building_1 = BuildingFactory.create(name="1")
    apartment_1 = ApartmentFactory.create(street_address="A01", building=building_1)
    apartment_2 = ApartmentFactory.create(street_address="B01", building=building_1)
    ApartmentFactory.create(street_address="C01", building=building_1)

    building_2 = BuildingFactory.create(name="2")
    apartment_3 = ApartmentFactory.create(street_address="A10", building=building_2)
    ApartmentFactory.create(street_address="C11", building=building_2)

    building_3 = BuildingFactory.create(name="3")
    apartment_4 = ApartmentFactory.create(street_address="B20", building=building_3)

    query = """
        query {
          buildings: pagedBuildings(orderBy: "name") {
            edges {
              node {
                pk
                name
                apartmentsWithA: apartments(streetAddress_Istartswith: "A") {
                  edges {
                    node {
                      pk
                    }
                  }
                }
                apartmentsWithB: apartments(streetAddress_Istartswith: "B") {
                  edges {
                    node {
                      pk
                    }
                  }
                }
              }
            }
          }
          allBuildings: pagedBuildings(orderBy: "-name") {
            edges {
              node {
                name
              }
            }
          }
        }
    """

    response = graphql_client(query)
    assert response.full_content == {
        "data": {
            "buildings": {
                "edges": [
                    {
                        "node": {
                            "pk": building_1.pk,
                            "name": building_1.name,
                            "apartmentsWithA": {
                                "edges": [
                                    {"node": {"pk": apartment_1.pk}},
                                ],
                            },
                            "apartmentsWithB": {
                                "edges": [
                                    {"node": {"pk": apartment_2.pk}},
                                ],
                            },
                        },
                    },
                    {
                        "node": {
                            "pk": building_2.pk,
                            "name": building_2.name,
                            "apartmentsWithA": {
                                "edges": [
                                    {"node": {"pk": apartment_3.pk}},
                                ],
                            },
                            "apartmentsWithB": {
                                "edges": [],
                            },
                        },
                    },
                    {
                        "node": {
                            "pk": building_3.pk,
                            "name": building_3.name,
                            "apartmentsWithA": {
                                "edges": [],
                            },
                            "apartmentsWithB": {
                                "edges": [
                                    {"node": {"pk": apartment_4.pk}},
                                ],
                            },
                        },
                    },
                ],
            },
            "allBuildings": {
                "edges": [
                    {"node": {"name": building_3.name}},
                    {"node": {"name": building_2.name}},
                    {"node": {"name": building_1.name}},
                ]
            },
        }
    }

    assert response.queries.count == 6, response.queries.log
