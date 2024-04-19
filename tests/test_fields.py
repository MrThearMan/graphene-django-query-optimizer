import datetime

import pytest

from tests.factories import (
    ApartmentFactory,
    BuildingFactory,
    DeveloperFactory,
    HousingCompanyFactory,
    OwnerFactory,
    PropertyManagerFactory,
    RealEstateFactory,
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


def test_fields__alternate_field__to_one_related(graphql_client):
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
    housing_company_1 = HousingCompanyFactory.create()
    housing_company_2 = HousingCompanyFactory.create()
    housing_company_3 = HousingCompanyFactory.create()
    RealEstateFactory.create(name="1", housing_company=housing_company_1)
    RealEstateFactory.create(name="2", housing_company=housing_company_1)
    RealEstateFactory.create(name="3", housing_company=housing_company_1)
    RealEstateFactory.create(name="4", housing_company=housing_company_2)
    RealEstateFactory.create(name="5", housing_company=housing_company_2)
    RealEstateFactory.create(name="6", housing_company=housing_company_3)

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
            {
                "node": {
                    "realEstatesAlt": [
                        {"name": "1"},
                        {"name": "2"},
                        {"name": "3"},
                    ],
                },
            },
            {
                "node": {
                    "realEstatesAlt": [
                        {"name": "4"},
                        {"name": "5"},
                    ],
                },
            },
            {
                "node": {
                    "realEstatesAlt": [
                        {"name": "6"},
                    ],
                },
            },
        ],
    }


def test_fields__alternate_field__many_to_many_related(graphql_client):
    developer_1 = DeveloperFactory.create(name="1")
    developer_2 = DeveloperFactory.create(name="2")
    developer_3 = DeveloperFactory.create(name="3")
    developer_4 = DeveloperFactory.create(name="4")
    developer_5 = DeveloperFactory.create(name="5")

    HousingCompanyFactory.create(developers=[developer_1, developer_2, developer_3])
    HousingCompanyFactory.create(developers=[developer_3, developer_4, developer_5])
    HousingCompanyFactory.create(developers__name="6")

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
            {
                "node": {
                    "developersAlt": [
                        {"name": "1"},
                        {"name": "2"},
                        {"name": "3"},
                    ],
                },
            },
            {
                "node": {
                    "developersAlt": [
                        {"name": "3"},
                        {"name": "4"},
                        {"name": "5"},
                    ],
                },
            },
            {
                "node": {
                    "developersAlt": [
                        {"name": "6"},
                    ],
                },
            },
        ],
    }


def test_fields__alternate_field__many_to_many_related__reverse(graphql_client):
    housing_company_1 = HousingCompanyFactory.create(name="1")
    housing_company_2 = HousingCompanyFactory.create(name="2")
    housing_company_3 = HousingCompanyFactory.create(name="3")
    housing_company_4 = HousingCompanyFactory.create(name="4")
    housing_company_5 = HousingCompanyFactory.create(name="5")
    housing_company_6 = HousingCompanyFactory.create(name="6")

    DeveloperFactory.create(housingcompany_set=[housing_company_1, housing_company_2, housing_company_3])
    DeveloperFactory.create(housingcompany_set=[housing_company_3, housing_company_4, housing_company_5])
    DeveloperFactory.create(housingcompany_set=[housing_company_1, housing_company_3, housing_company_6])

    query = """
        query {
          pagedDevelopers {
            edges {
              node {
                housingCompanies {
                  name
                }
              }
            }
          }
        }
    """

    response = graphql_client(query)
    assert response.no_errors, response.errors

    # 1 query for counting developers
    # 1 query for fetching developers
    # 1 query for fetching nested housing companies (to the alternate field)
    assert response.queries.count == 3, response.queries.log

    assert response.queries[0] == has(
        "COUNT(*)",
        'FROM "example_developer"',
    )
    assert response.queries[1] == has(
        'FROM "example_developer"',
    )
    assert response.queries[2] == has(
        'FROM "example_housingcompany"',
    )

    assert response.content == {
        "edges": [
            {
                "node": {
                    "housingCompanies": [
                        {"name": "1"},
                        {"name": "2"},
                        {"name": "3"},
                    ],
                },
            },
            {
                "node": {
                    "housingCompanies": [
                        {"name": "3"},
                        {"name": "4"},
                        {"name": "5"},
                    ],
                },
            },
            {
                "node": {
                    "housingCompanies": [
                        {"name": "1"},
                        {"name": "3"},
                        {"name": "6"},
                    ],
                },
            },
        ]
    }


def test_fields__alternate_field__many_to_many_related__with_original(graphql_client):
    developer_1 = DeveloperFactory.create(name="1")
    developer_2 = DeveloperFactory.create(name="2")
    developer_3 = DeveloperFactory.create(name="3")
    developer_4 = DeveloperFactory.create(name="4")
    developer_5 = DeveloperFactory.create(name="5")
    developer_6 = DeveloperFactory.create(name="6")

    HousingCompanyFactory.create(developers=[developer_1, developer_2, developer_3])
    HousingCompanyFactory.create(developers=[developer_3, developer_4, developer_5])
    HousingCompanyFactory.create(developers=[developer_1, developer_3, developer_6])

    query = """
        query {
          pagedHousingCompanies {
            edges {
              node {
                developersAlt {
                  name
                }
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

    # 1 query for counting housing companies
    # 1 query for fetching housing companies
    # 1 query for fetching nested developers
    # 1 query for fetching nested developers (to the alternate field)
    assert response.queries.count == 4, response.queries.log

    assert response.queries[0] == has(
        "COUNT(*)",
        'FROM "example_housingcompany"',
    )
    assert response.queries[1] == has(
        'FROM "example_housingcompany"',
    )
    assert response.queries[2] == has(
        'FROM "example_developer"',
        (
            "ROW_NUMBER() OVER "
            '(PARTITION BY "example_housingcompany_developers"."housingcompany_id" ORDER BY "example_developer"."id")'
        ),
    )
    assert response.queries[3] == has(
        'FROM "example_developer"',
        (
            "ROW_NUMBER() OVER "
            '(PARTITION BY "example_housingcompany_developers"."housingcompany_id" ORDER BY "example_developer"."id")'
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
                    "developersAlt": [
                        {"name": "1"},
                        {"name": "2"},
                        {"name": "3"},
                    ],
                },
            },
            {
                "node": {
                    "developers": {
                        "edges": [
                            {"node": {"name": "3"}},
                            {"node": {"name": "4"}},
                            {"node": {"name": "5"}},
                        ],
                    },
                    "developersAlt": [
                        {"name": "3"},
                        {"name": "4"},
                        {"name": "5"},
                    ],
                },
            },
            {
                "node": {
                    "developers": {
                        "edges": [
                            {"node": {"name": "1"}},
                            {"node": {"name": "3"}},
                            {"node": {"name": "6"}},
                        ],
                    },
                    "developersAlt": [
                        {"name": "1"},
                        {"name": "3"},
                        {"name": "6"},
                    ],
                },
            },
        ],
    }


def test_fields__alternate_field__many_to_many_related__reverse__with_original(graphql_client):
    housing_company_1 = HousingCompanyFactory.create(name="1")
    housing_company_2 = HousingCompanyFactory.create(name="2")
    housing_company_3 = HousingCompanyFactory.create(name="3")
    housing_company_4 = HousingCompanyFactory.create(name="4")
    housing_company_5 = HousingCompanyFactory.create(name="5")
    housing_company_6 = HousingCompanyFactory.create(name="6")

    DeveloperFactory.create(housingcompany_set=[housing_company_1, housing_company_2, housing_company_3])
    DeveloperFactory.create(housingcompany_set=[housing_company_3, housing_company_4, housing_company_5])
    DeveloperFactory.create(housingcompany_set=[housing_company_1, housing_company_3, housing_company_6])

    query = """
        query {
          pagedDevelopers {
            edges {
              node {
                housingCompanies {
                  name
                }
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

    # 1 query for counting developers
    # 1 query for fetching developers
    # 1 query for fetching nested housing companies
    # 1 query for fetching nested housing companies (to the alternate field)
    assert response.queries.count == 4, response.queries.log

    assert response.queries[0] == has(
        "COUNT(*)",
        'FROM "example_developer"',
    )
    assert response.queries[1] == has(
        'FROM "example_developer"',
    )
    assert response.queries[2] == has(
        'FROM "example_housingcompany"',
        (
            "ROW_NUMBER() OVER "
            '(PARTITION BY "example_housingcompany_developers"."developer_id" ORDER BY "example_housingcompany"."id"'
        ),
    )
    assert response.queries[3] == has(
        'FROM "example_housingcompany"',
        (
            "ROW_NUMBER() OVER "
            '(PARTITION BY "example_housingcompany_developers"."developer_id" ORDER BY "example_housingcompany"."id"'
        ),
    )

    assert response.content == {
        "edges": [
            {
                "node": {
                    "housingCompanies": [
                        {"name": "1"},
                        {"name": "2"},
                        {"name": "3"},
                    ],
                    "housingcompanySet": {
                        "edges": [
                            {"node": {"name": "1"}},
                            {"node": {"name": "2"}},
                            {"node": {"name": "3"}},
                        ]
                    },
                }
            },
            {
                "node": {
                    "housingCompanies": [
                        {"name": "3"},
                        {"name": "4"},
                        {"name": "5"},
                    ],
                    "housingcompanySet": {
                        "edges": [
                            {"node": {"name": "3"}},
                            {"node": {"name": "4"}},
                            {"node": {"name": "5"}},
                        ]
                    },
                }
            },
            {
                "node": {
                    "housingCompanies": [
                        {"name": "1"},
                        {"name": "3"},
                        {"name": "6"},
                    ],
                    "housingcompanySet": {
                        "edges": [
                            {"node": {"name": "1"}},
                            {"node": {"name": "3"}},
                            {"node": {"name": "6"}},
                        ]
                    },
                }
            },
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


def test_fields__pre_field(graphql_client):
    owner_1 = OwnerFactory.create()
    owner_2 = OwnerFactory.create()
    owner_3 = OwnerFactory.create()

    query = """
        query {
          allOwners {
            preField(foo:0)
          }
        }
    """

    response = graphql_client(query)
    assert response.no_errors, response.errors

    # 1 query for fetching Owners
    assert response.queries.count == 1, response.queries.log

    assert response.content == [
        {"preField": f"{owner_1.name}-0"},
        {"preField": f"{owner_2.name}-0"},
        {"preField": f"{owner_3.name}-0"},
    ]
