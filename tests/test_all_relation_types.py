import pytest

from .factories.example import ExampleFactory

pytestmark = [
    pytest.mark.django_db,
]

###############################################################################################


def test_relations__forward_one_to_one__forward_one_to_one(graphql_client):
    ExampleFactory.create(forward_one_to_one_field__forward_one_to_one_field__name="1")
    ExampleFactory.create(forward_one_to_one_field__forward_one_to_one_field__name="2")
    ExampleFactory.create(forward_one_to_one_field__forward_one_to_one_field__name="3")

    query = """
        query {
          examples {
            forwardOneToOneField {
              forwardOneToOneField {
                name
              }
            }
          }
        }
    """

    response = graphql_client(query)
    assert response.no_errors, response.errors

    # 1 query for all examples, forward one-to-one relations, and nested forward one-to-one relations
    assert response.queries.count == 1, response.queries.log

    assert response.content == [
        {"forwardOneToOneField": {"forwardOneToOneField": {"name": "1"}}},
        {"forwardOneToOneField": {"forwardOneToOneField": {"name": "2"}}},
        {"forwardOneToOneField": {"forwardOneToOneField": {"name": "3"}}},
    ]


def test_relations__forward_one_to_one__forward_many_to_one(graphql_client):
    ExampleFactory.create(forward_one_to_one_field__forward_many_to_one_field__name="1")
    ExampleFactory.create(forward_one_to_one_field__forward_many_to_one_field__name="2")
    ExampleFactory.create(forward_one_to_one_field__forward_many_to_one_field__name="3")

    query = """
        query {
          examples {
            forwardOneToOneField {
              forwardManyToOneField {
                name
              }
            }
          }
        }
    """

    response = graphql_client(query)
    assert response.no_errors, response.errors

    # 1 query for all examples, forward one-to-one relations, and nested forward many-to-one relations
    assert response.queries.count == 1, response.queries.log

    assert response.content == [
        {"forwardOneToOneField": {"forwardManyToOneField": {"name": "1"}}},
        {"forwardOneToOneField": {"forwardManyToOneField": {"name": "2"}}},
        {"forwardOneToOneField": {"forwardManyToOneField": {"name": "3"}}},
    ]


def test_relations__forward_one_to_one__forward_many_to_many(graphql_client):
    ExampleFactory.create(forward_one_to_one_field__forward_many_to_many_fields__name="1")
    ExampleFactory.create(forward_one_to_one_field__forward_many_to_many_fields__name="2")
    ExampleFactory.create(forward_one_to_one_field__forward_many_to_many_fields__name="3")

    query = """
        query {
          examples {
            forwardOneToOneField {
              forwardManyToManyFields {
                name
              }
            }
          }
        }
    """

    response = graphql_client(query)
    assert response.no_errors, response.errors

    # 1 query for all examples, forward one-to-one relations
    # 1 query for all nested forward many-to-many relations
    assert response.queries.count == 2, response.queries.log

    assert response.content == [
        {"forwardOneToOneField": {"forwardManyToManyFields": [{"name": "1"}]}},
        {"forwardOneToOneField": {"forwardManyToManyFields": [{"name": "2"}]}},
        {"forwardOneToOneField": {"forwardManyToManyFields": [{"name": "3"}]}},
    ]


def test_relations__forward_one_to_one__reverse_one_to_one(graphql_client):
    ExampleFactory.create(forward_one_to_one_field__reverse_one_to_one_rel__name="1")
    ExampleFactory.create(forward_one_to_one_field__reverse_one_to_one_rel__name="2")
    ExampleFactory.create(forward_one_to_one_field__reverse_one_to_one_rel__name="3")

    query = """
        query {
          examples {
            forwardOneToOneField {
              reverseOneToOneRel {
                name
              }
            }
          }
        }
    """

    response = graphql_client(query)
    assert response.no_errors, response.errors

    # 1 query for all examples, forward one-to-one relations and nested reverse one-to-one relations
    assert response.queries.count == 1, response.queries.log

    assert response.content == [
        {"forwardOneToOneField": {"reverseOneToOneRel": {"name": "1"}}},
        {"forwardOneToOneField": {"reverseOneToOneRel": {"name": "2"}}},
        {"forwardOneToOneField": {"reverseOneToOneRel": {"name": "3"}}},
    ]


def test_relations__forward_one_to_one__reverse_one_to_many(graphql_client):
    ExampleFactory.create(forward_one_to_one_field__reverse_one_to_many_rels__name="1")
    ExampleFactory.create(forward_one_to_one_field__reverse_one_to_many_rels__name="2")
    ExampleFactory.create(forward_one_to_one_field__reverse_one_to_many_rels__name="3")

    query = """
        query {
          examples {
            forwardOneToOneField {
              reverseOneToManyRels {
                name
              }
            }
          }
        }
    """

    response = graphql_client(query)
    assert response.no_errors, response.errors

    # 1 query for all examples, forward one-to-one relations
    # 1 query for all nested reverse one-to-many relations
    assert response.queries.count == 2, response.queries.log

    assert response.content == [
        {"forwardOneToOneField": {"reverseOneToManyRels": [{"name": "1"}]}},
        {"forwardOneToOneField": {"reverseOneToManyRels": [{"name": "2"}]}},
        {"forwardOneToOneField": {"reverseOneToManyRels": [{"name": "3"}]}},
    ]


def test_relations__forward_one_to_one__reverse_many_to_many(graphql_client):
    ExampleFactory.create(forward_one_to_one_field__reverse_many_to_many_rels__name="1")
    ExampleFactory.create(forward_one_to_one_field__reverse_many_to_many_rels__name="2")
    ExampleFactory.create(forward_one_to_one_field__reverse_many_to_many_rels__name="3")

    query = """
        query {
          examples {
            forwardOneToOneField {
              reverseManyToManyRels {
                name
              }
            }
          }
        }
    """

    response = graphql_client(query)
    assert response.no_errors, response.errors

    # 1 query for all examples, forward one-to-one relations
    # 1 query for all nested reverse many-to-many relations
    assert response.queries.count == 2, response.queries.log

    assert response.content == [
        {"forwardOneToOneField": {"reverseManyToManyRels": [{"name": "1"}]}},
        {"forwardOneToOneField": {"reverseManyToManyRels": [{"name": "2"}]}},
        {"forwardOneToOneField": {"reverseManyToManyRels": [{"name": "3"}]}},
    ]


###############################################################################################


def test_relations__forward_many_to_one__forward_one_to_one(graphql_client):
    ExampleFactory.create(forward_many_to_one_field__forward_one_to_one_field__name="1")
    ExampleFactory.create(forward_many_to_one_field__forward_one_to_one_field__name="2")
    ExampleFactory.create(forward_many_to_one_field__forward_one_to_one_field__name="3")

    query = """
        query {
          examples {
            forwardManyToOneField {
              forwardOneToOneField {
                name
              }
            }
          }
        }
    """

    response = graphql_client(query)
    assert response.no_errors, response.errors

    # 1 query for all examples, forward many-to-one relations, and nested forward one-to-one relations
    assert response.queries.count == 1, response.queries.log

    assert response.content == [
        {"forwardManyToOneField": {"forwardOneToOneField": {"name": "1"}}},
        {"forwardManyToOneField": {"forwardOneToOneField": {"name": "2"}}},
        {"forwardManyToOneField": {"forwardOneToOneField": {"name": "3"}}},
    ]


def test_relations__forward_many_to_one__forward_many_to_one(graphql_client):
    ExampleFactory.create(forward_many_to_one_field__forward_many_to_one_field__name="1")
    ExampleFactory.create(forward_many_to_one_field__forward_many_to_one_field__name="2")
    ExampleFactory.create(forward_many_to_one_field__forward_many_to_one_field__name="3")

    query = """
        query {
          examples {
            forwardManyToOneField {
              forwardManyToOneField {
                name
              }
            }
          }
        }
    """

    response = graphql_client(query)
    assert response.no_errors, response.errors

    # 1 query for all examples, forward many-to-one relations, and nested forward many-to-one relations
    assert response.queries.count == 1, response.queries.log

    assert response.content == [
        {"forwardManyToOneField": {"forwardManyToOneField": {"name": "1"}}},
        {"forwardManyToOneField": {"forwardManyToOneField": {"name": "2"}}},
        {"forwardManyToOneField": {"forwardManyToOneField": {"name": "3"}}},
    ]


def test_relations__forward_many_to_one__forward_many_to_many(graphql_client):
    ExampleFactory.create(forward_many_to_one_field__forward_many_to_many_fields__name="1")
    ExampleFactory.create(forward_many_to_one_field__forward_many_to_many_fields__name="2")
    ExampleFactory.create(forward_many_to_one_field__forward_many_to_many_fields__name="3")

    query = """
        query {
          examples {
            forwardManyToOneField {
              forwardManyToManyFields {
                name
              }
            }
          }
        }
    """

    response = graphql_client(query)
    assert response.no_errors, response.errors

    # 1 query for all examples, forward many-to-one relations
    # 1 query for all nested forward many-to-many relations
    assert response.queries.count == 2, response.queries.log

    assert response.content == [
        {"forwardManyToOneField": {"forwardManyToManyFields": [{"name": "1"}]}},
        {"forwardManyToOneField": {"forwardManyToManyFields": [{"name": "2"}]}},
        {"forwardManyToOneField": {"forwardManyToManyFields": [{"name": "3"}]}},
    ]


def test_relations__forward_many_to_one__reverse_one_to_one(graphql_client):
    ExampleFactory.create(forward_many_to_one_field__reverse_one_to_one_rel__name="1")
    ExampleFactory.create(forward_many_to_one_field__reverse_one_to_one_rel__name="2")
    ExampleFactory.create(forward_many_to_one_field__reverse_one_to_one_rel__name="3")

    query = """
        query {
          examples {
            forwardManyToOneField {
              reverseOneToOneRel {
                name
              }
            }
          }
        }
    """

    response = graphql_client(query)
    assert response.no_errors, response.errors

    # 1 query for all examples, forward many-to-one relations and nested reverse one-to-one relations
    assert response.queries.count == 1, response.queries.log

    assert response.content == [
        {"forwardManyToOneField": {"reverseOneToOneRel": {"name": "1"}}},
        {"forwardManyToOneField": {"reverseOneToOneRel": {"name": "2"}}},
        {"forwardManyToOneField": {"reverseOneToOneRel": {"name": "3"}}},
    ]


def test_relations__forward_many_to_one__reverse_one_to_many(graphql_client):
    ExampleFactory.create(forward_many_to_one_field__reverse_one_to_many_rels__name="1")
    ExampleFactory.create(forward_many_to_one_field__reverse_one_to_many_rels__name="2")
    ExampleFactory.create(forward_many_to_one_field__reverse_one_to_many_rels__name="3")

    query = """
        query {
          examples {
            forwardManyToOneField {
              reverseOneToManyRels {
                name
              }
            }
          }
        }
    """

    response = graphql_client(query)
    assert response.no_errors, response.errors

    # 1 query for all examples, forward many-to-one relations
    # 1 query for all nested reverse one-to-many relations
    assert response.queries.count == 2, response.queries.log

    assert response.content == [
        {"forwardManyToOneField": {"reverseOneToManyRels": [{"name": "1"}]}},
        {"forwardManyToOneField": {"reverseOneToManyRels": [{"name": "2"}]}},
        {"forwardManyToOneField": {"reverseOneToManyRels": [{"name": "3"}]}},
    ]


def test_relations__forward_many_to_one__reverse_many_to_many(graphql_client):
    ExampleFactory.create(forward_many_to_one_field__reverse_many_to_many_rels__name="1")
    ExampleFactory.create(forward_many_to_one_field__reverse_many_to_many_rels__name="2")
    ExampleFactory.create(forward_many_to_one_field__reverse_many_to_many_rels__name="3")

    query = """
        query {
          examples {
            forwardManyToOneField {
              reverseManyToManyRels {
                name
              }
            }
          }
        }
    """

    response = graphql_client(query)
    assert response.no_errors, response.errors

    # 1 query for all examples, forward many-to-one relations
    # 1 query for all nested reverse many-to-many relations
    assert response.queries.count == 2, response.queries.log

    assert response.content == [
        {"forwardManyToOneField": {"reverseManyToManyRels": [{"name": "1"}]}},
        {"forwardManyToOneField": {"reverseManyToManyRels": [{"name": "2"}]}},
        {"forwardManyToOneField": {"reverseManyToManyRels": [{"name": "3"}]}},
    ]


###############################################################################################


def test_relations__forward_many_to_many__forward_one_to_one(graphql_client):
    ExampleFactory.create(forward_many_to_many_fields__forward_one_to_one_field__name="1")
    ExampleFactory.create(forward_many_to_many_fields__forward_one_to_one_field__name="2")
    ExampleFactory.create(forward_many_to_many_fields__forward_one_to_one_field__name="3")

    query = """
        query {
          examples {
            forwardManyToManyFields {
              forwardOneToOneField {
                name
              }
            }
          }
        }
    """

    response = graphql_client(query)
    assert response.no_errors, response.errors

    # 1 query for all examples
    # 1 query fo all forward many-to-many relations, and nested forward one-to-one relations
    assert response.queries.count == 2, response.queries.log

    assert response.content == [
        {"forwardManyToManyFields": [{"forwardOneToOneField": {"name": "1"}}]},
        {"forwardManyToManyFields": [{"forwardOneToOneField": {"name": "2"}}]},
        {"forwardManyToManyFields": [{"forwardOneToOneField": {"name": "3"}}]},
    ]


def test_relations__forward_many_to_many__forward_many_to_one(graphql_client):
    ExampleFactory.create(forward_many_to_many_fields__forward_many_to_one_field__name="1")
    ExampleFactory.create(forward_many_to_many_fields__forward_many_to_one_field__name="2")
    ExampleFactory.create(forward_many_to_many_fields__forward_many_to_one_field__name="3")

    query = """
        query {
          examples {
            forwardManyToManyFields {
              forwardManyToOneField {
                name
              }
            }
          }
        }
    """

    response = graphql_client(query)
    assert response.no_errors, response.errors

    # 1 query for all examples
    # 1 query fo all forward many-to-many relations, and nested forward many-to-one relations
    assert response.queries.count == 2, response.queries.log

    assert response.content == [
        {"forwardManyToManyFields": [{"forwardManyToOneField": {"name": "1"}}]},
        {"forwardManyToManyFields": [{"forwardManyToOneField": {"name": "2"}}]},
        {"forwardManyToManyFields": [{"forwardManyToOneField": {"name": "3"}}]},
    ]


def test_relations__forward_many_to_many__forward_many_to_many(graphql_client):
    ExampleFactory.create(forward_many_to_many_fields__forward_many_to_many_fields__name="1")
    ExampleFactory.create(forward_many_to_many_fields__forward_many_to_many_fields__name="2")
    ExampleFactory.create(forward_many_to_many_fields__forward_many_to_many_fields__name="3")

    query = """
        query {
          examples {
            forwardManyToManyFields {
              forwardManyToManyFields {
                name
              }
            }
          }
        }
    """

    response = graphql_client(query)
    assert response.no_errors, response.errors

    # 1 query for all examples
    # 1 query fo all forward many-to-many relations
    # 1 query for all nested forward many-to-many relations
    assert response.queries.count == 3, response.queries.log

    assert response.content == [
        {"forwardManyToManyFields": [{"forwardManyToManyFields": [{"name": "1"}]}]},
        {"forwardManyToManyFields": [{"forwardManyToManyFields": [{"name": "2"}]}]},
        {"forwardManyToManyFields": [{"forwardManyToManyFields": [{"name": "3"}]}]},
    ]


def test_relations__forward_many_to_many__reverse_one_to_one(graphql_client):
    ExampleFactory.create(forward_many_to_many_fields__reverse_one_to_one_rel__name="1")
    ExampleFactory.create(forward_many_to_many_fields__reverse_one_to_one_rel__name="2")
    ExampleFactory.create(forward_many_to_many_fields__reverse_one_to_one_rel__name="3")

    query = """
        query {
          examples {
            forwardManyToManyFields {
              reverseOneToOneRel {
                name
              }
            }
          }
        }
    """

    response = graphql_client(query)
    assert response.no_errors, response.errors

    # 1 query for all examples
    # 1 query for all forward many-to-many relations and nested reverse one-to-one relations
    assert response.queries.count == 2, response.queries.log

    assert response.content == [
        {"forwardManyToManyFields": [{"reverseOneToOneRel": {"name": "1"}}]},
        {"forwardManyToManyFields": [{"reverseOneToOneRel": {"name": "2"}}]},
        {"forwardManyToManyFields": [{"reverseOneToOneRel": {"name": "3"}}]},
    ]


def test_relations__forward_many_to_many__reverse_one_to_many(graphql_client):
    ExampleFactory.create(forward_many_to_many_fields__reverse_one_to_many_rels__name="1")
    ExampleFactory.create(forward_many_to_many_fields__reverse_one_to_many_rels__name="2")
    ExampleFactory.create(forward_many_to_many_fields__reverse_one_to_many_rels__name="3")

    query = """
        query {
          examples {
            forwardManyToManyFields {
              reverseOneToManyRels {
                name
              }
            }
          }
        }
    """

    response = graphql_client(query)
    assert response.no_errors, response.errors

    # 1 query for all examples
    # 1 query for all forward many-to-many relations
    # 1 query for all nested reverse one-to-many relations
    assert response.queries.count == 3, response.queries.log

    assert response.content == [
        {"forwardManyToManyFields": [{"reverseOneToManyRels": [{"name": "1"}]}]},
        {"forwardManyToManyFields": [{"reverseOneToManyRels": [{"name": "2"}]}]},
        {"forwardManyToManyFields": [{"reverseOneToManyRels": [{"name": "3"}]}]},
    ]


def test_relations__forward_many_to_many__reverse_many_to_many(graphql_client):
    ExampleFactory.create(forward_many_to_many_fields__reverse_many_to_many_rels__name="1")
    ExampleFactory.create(forward_many_to_many_fields__reverse_many_to_many_rels__name="2")
    ExampleFactory.create(forward_many_to_many_fields__reverse_many_to_many_rels__name="3")

    query = """
        query {
          examples {
            forwardManyToManyFields {
              reverseManyToManyRels {
                name
              }
            }
          }
        }
    """

    response = graphql_client(query)
    assert response.no_errors, response.errors

    # 1 query for all examples
    # 1 query for all forward many-to-many relations
    # 1 query for all nested reverse many-to-many relations
    assert response.queries.count == 3, response.queries.log

    assert response.content == [
        {"forwardManyToManyFields": [{"reverseManyToManyRels": [{"name": "1"}]}]},
        {"forwardManyToManyFields": [{"reverseManyToManyRels": [{"name": "2"}]}]},
        {"forwardManyToManyFields": [{"reverseManyToManyRels": [{"name": "3"}]}]},
    ]


###############################################################################################


def test_relations__reverse_one_to_one__forward_one_to_one(graphql_client):
    ExampleFactory.create(reverse_one_to_one_rel__forward_one_to_one_field__name="1")
    ExampleFactory.create(reverse_one_to_one_rel__forward_one_to_one_field__name="2")
    ExampleFactory.create(reverse_one_to_one_rel__forward_one_to_one_field__name="3")

    query = """
        query {
          examples {
            reverseOneToOneRel {
              forwardOneToOneField {
                name
              }
            }
          }
        }
    """

    response = graphql_client(query)
    assert response.no_errors, response.errors

    # 1 query for all examples, reverse one-to-one relations, and nested forward one-to-one relations
    assert response.queries.count == 1, response.queries.log

    assert response.content == [
        {"reverseOneToOneRel": {"forwardOneToOneField": {"name": "1"}}},
        {"reverseOneToOneRel": {"forwardOneToOneField": {"name": "2"}}},
        {"reverseOneToOneRel": {"forwardOneToOneField": {"name": "3"}}},
    ]


def test_relations__reverse_one_to_one__forward_many_to_one(graphql_client):
    ExampleFactory.create(reverse_one_to_one_rel__forward_many_to_one_field__name="1")
    ExampleFactory.create(reverse_one_to_one_rel__forward_many_to_one_field__name="2")
    ExampleFactory.create(reverse_one_to_one_rel__forward_many_to_one_field__name="3")

    query = """
        query {
          examples {
            reverseOneToOneRel {
              forwardManyToOneField {
                name
              }
            }
          }
        }
    """

    response = graphql_client(query)
    assert response.no_errors, response.errors

    # 1 query for all examples, reverse one-to-one relations, and nested forward many-to-one relations
    assert response.queries.count == 1, response.queries.log

    assert response.content == [
        {"reverseOneToOneRel": {"forwardManyToOneField": {"name": "1"}}},
        {"reverseOneToOneRel": {"forwardManyToOneField": {"name": "2"}}},
        {"reverseOneToOneRel": {"forwardManyToOneField": {"name": "3"}}},
    ]


def test_relations__reverse_one_to_one__forward_many_to_many(graphql_client):
    ExampleFactory.create(reverse_one_to_one_rel__forward_many_to_many_fields__name="1")
    ExampleFactory.create(reverse_one_to_one_rel__forward_many_to_many_fields__name="2")
    ExampleFactory.create(reverse_one_to_one_rel__forward_many_to_many_fields__name="3")

    query = """
        query {
          examples {
            reverseOneToOneRel {
              forwardManyToManyFields {
                name
              }
            }
          }
        }
    """

    response = graphql_client(query)
    assert response.no_errors, response.errors

    # 1 query for all examples, reverse one-to-one relations
    # 1 query for all nested forward many-to-many relations
    assert response.queries.count == 2, response.queries.log

    assert response.content == [
        {"reverseOneToOneRel": {"forwardManyToManyFields": [{"name": "1"}]}},
        {"reverseOneToOneRel": {"forwardManyToManyFields": [{"name": "2"}]}},
        {"reverseOneToOneRel": {"forwardManyToManyFields": [{"name": "3"}]}},
    ]


def test_relations__reverse_one_to_one__reverse_one_to_one(graphql_client):
    ExampleFactory.create(reverse_one_to_one_rel__reverse_one_to_one_rel__name="1")
    ExampleFactory.create(reverse_one_to_one_rel__reverse_one_to_one_rel__name="2")
    ExampleFactory.create(reverse_one_to_one_rel__reverse_one_to_one_rel__name="3")

    query = """
        query {
          examples {
            reverseOneToOneRel {
              reverseOneToOneRel {
                name
              }
            }
          }
        }
    """

    response = graphql_client(query)
    assert response.no_errors, response.errors

    # 1 query for all examples, reverse one-to-one relations and nested reverse one-to-one relations
    assert response.queries.count == 1, response.queries.log

    assert response.content == [
        {"reverseOneToOneRel": {"reverseOneToOneRel": {"name": "1"}}},
        {"reverseOneToOneRel": {"reverseOneToOneRel": {"name": "2"}}},
        {"reverseOneToOneRel": {"reverseOneToOneRel": {"name": "3"}}},
    ]


def test_relations__reverse_one_to_one__reverse_one_to_many(graphql_client):
    ExampleFactory.create(reverse_one_to_one_rel__reverse_one_to_many_rels__name="1")
    ExampleFactory.create(reverse_one_to_one_rel__reverse_one_to_many_rels__name="2")
    ExampleFactory.create(reverse_one_to_one_rel__reverse_one_to_many_rels__name="3")

    query = """
        query {
          examples {
            reverseOneToOneRel {
              reverseOneToManyRels {
                name
              }
            }
          }
        }
    """

    response = graphql_client(query)
    assert response.no_errors, response.errors

    # 1 query for all examples, reverse one-to-one relations
    # 1 query for all nested reverse one-to-many relations
    assert response.queries.count == 2, response.queries.log

    assert response.content == [
        {"reverseOneToOneRel": {"reverseOneToManyRels": [{"name": "1"}]}},
        {"reverseOneToOneRel": {"reverseOneToManyRels": [{"name": "2"}]}},
        {"reverseOneToOneRel": {"reverseOneToManyRels": [{"name": "3"}]}},
    ]


def test_relations__reverse_one_to_one__reverse_many_to_many(graphql_client):
    ExampleFactory.create(reverse_one_to_one_rel__reverse_many_to_many_rels__name="1")
    ExampleFactory.create(reverse_one_to_one_rel__reverse_many_to_many_rels__name="2")
    ExampleFactory.create(reverse_one_to_one_rel__reverse_many_to_many_rels__name="3")

    query = """
        query {
          examples {
            reverseOneToOneRel {
              reverseManyToManyRels {
                name
              }
            }
          }
        }
    """

    response = graphql_client(query)
    assert response.no_errors, response.errors

    # 1 query for all examples, reverse one-to-one relations
    # 1 query for all nested reverse many-to-many relations
    assert response.queries.count == 2, response.queries.log

    assert response.content == [
        {"reverseOneToOneRel": {"reverseManyToManyRels": [{"name": "1"}]}},
        {"reverseOneToOneRel": {"reverseManyToManyRels": [{"name": "2"}]}},
        {"reverseOneToOneRel": {"reverseManyToManyRels": [{"name": "3"}]}},
    ]


###############################################################################################


def test_relations__reverse_one_to_many__forward_one_to_one(graphql_client):
    ExampleFactory.create(reverse_one_to_many_rels__forward_one_to_one_field__name="1")
    ExampleFactory.create(reverse_one_to_many_rels__forward_one_to_one_field__name="2")
    ExampleFactory.create(reverse_one_to_many_rels__forward_one_to_one_field__name="3")

    query = """
        query {
          examples {
            reverseOneToManyRels {
              forwardOneToOneField {
                name
              }
            }
          }
        }
    """

    response = graphql_client(query)
    assert response.no_errors, response.errors

    # 1 query for all examples
    # 1 query for all reverse one-to-many relations query and nested forward one-to-one relations
    assert response.queries.count == 2, response.queries.log

    assert response.content == [
        {"reverseOneToManyRels": [{"forwardOneToOneField": {"name": "1"}}]},
        {"reverseOneToManyRels": [{"forwardOneToOneField": {"name": "2"}}]},
        {"reverseOneToManyRels": [{"forwardOneToOneField": {"name": "3"}}]},
    ]


def test_relations__reverse_one_to_many__forward_many_to_one(graphql_client):
    ExampleFactory.create(reverse_one_to_many_rels__forward_many_to_one_field__name="1")
    ExampleFactory.create(reverse_one_to_many_rels__forward_many_to_one_field__name="2")
    ExampleFactory.create(reverse_one_to_many_rels__forward_many_to_one_field__name="3")

    query = """
        query {
          examples {
            reverseOneToManyRels {
              forwardManyToOneField {
                name
              }
            }
          }
        }
    """

    response = graphql_client(query)
    assert response.no_errors, response.errors

    # 1 query for all examples
    # 1 query for all reverse one-to-many relations query and nested forward many-to-one relations
    assert response.queries.count == 2, response.queries.log

    assert response.content == [
        {"reverseOneToManyRels": [{"forwardManyToOneField": {"name": "1"}}]},
        {"reverseOneToManyRels": [{"forwardManyToOneField": {"name": "2"}}]},
        {"reverseOneToManyRels": [{"forwardManyToOneField": {"name": "3"}}]},
    ]


def test_relations__reverse_one_to_many__forward_many_to_many(graphql_client):
    ExampleFactory.create(reverse_one_to_many_rels__forward_many_to_many_fields__name="1")
    ExampleFactory.create(reverse_one_to_many_rels__forward_many_to_many_fields__name="2")
    ExampleFactory.create(reverse_one_to_many_rels__forward_many_to_many_fields__name="3")

    query = """
        query {
          examples {
            reverseOneToManyRels {
              forwardManyToManyFields {
                name
              }
            }
          }
        }
    """

    response = graphql_client(query)
    assert response.no_errors, response.errors

    # 1 query for all examples
    # 1 query for all reverse one-to-many relations
    # 1 query for all nested forward many-to-many relations
    assert response.queries.count == 3, response.queries.log

    assert response.content == [
        {"reverseOneToManyRels": [{"forwardManyToManyFields": [{"name": "1"}]}]},
        {"reverseOneToManyRels": [{"forwardManyToManyFields": [{"name": "2"}]}]},
        {"reverseOneToManyRels": [{"forwardManyToManyFields": [{"name": "3"}]}]},
    ]


def test_relations__reverse_one_to_many__reverse_one_to_one(graphql_client):
    ExampleFactory.create(reverse_one_to_many_rels__reverse_one_to_one_rel__name="1")
    ExampleFactory.create(reverse_one_to_many_rels__reverse_one_to_one_rel__name="2")
    ExampleFactory.create(reverse_one_to_many_rels__reverse_one_to_one_rel__name="3")

    query = """
        query {
          examples {
            reverseOneToManyRels {
              reverseOneToOneRel {
                name
              }
            }
          }
        }
    """

    response = graphql_client(query)
    assert response.no_errors, response.errors

    # 1 query for all examples
    # 1 query for all reverse one-to-many relations query and nested reverse one-to-one relations
    assert response.queries.count == 2, response.queries.log

    assert response.content == [
        {"reverseOneToManyRels": [{"reverseOneToOneRel": {"name": "1"}}]},
        {"reverseOneToManyRels": [{"reverseOneToOneRel": {"name": "2"}}]},
        {"reverseOneToManyRels": [{"reverseOneToOneRel": {"name": "3"}}]},
    ]


def test_relations__reverse_one_to_many__reverse_one_to_many(graphql_client):
    ExampleFactory.create(reverse_one_to_many_rels__reverse_one_to_many_rels__name="1")
    ExampleFactory.create(reverse_one_to_many_rels__reverse_one_to_many_rels__name="2")
    ExampleFactory.create(reverse_one_to_many_rels__reverse_one_to_many_rels__name="3")

    query = """
        query {
          examples {
            reverseOneToManyRels {
              reverseOneToManyRels {
                name
              }
            }
          }
        }
    """

    response = graphql_client(query)
    assert response.no_errors, response.errors

    # 1 query for all examples
    # 1 query for all reverse one-to-many relations
    # 1 query for all nested reverse one-to-many relations
    assert response.queries.count == 3, response.queries.log

    assert response.content == [
        {"reverseOneToManyRels": [{"reverseOneToManyRels": [{"name": "1"}]}]},
        {"reverseOneToManyRels": [{"reverseOneToManyRels": [{"name": "2"}]}]},
        {"reverseOneToManyRels": [{"reverseOneToManyRels": [{"name": "3"}]}]},
    ]


def test_relations__reverse_one_to_many__reverse_many_to_many(graphql_client):
    ExampleFactory.create(reverse_one_to_many_rels__reverse_many_to_many_rels__name="1")
    ExampleFactory.create(reverse_one_to_many_rels__reverse_many_to_many_rels__name="2")
    ExampleFactory.create(reverse_one_to_many_rels__reverse_many_to_many_rels__name="3")

    query = """
        query {
          examples {
            reverseOneToManyRels {
              reverseManyToManyRels {
                name
              }
            }
          }
        }
    """

    response = graphql_client(query)
    assert response.no_errors, response.errors

    # 1 query for all examples
    # 1 query for all reverse one-to-many relations
    # 1 query for all nested reverse many-to-many relations
    assert response.queries.count == 3, response.queries.log

    assert response.content == [
        {"reverseOneToManyRels": [{"reverseManyToManyRels": [{"name": "1"}]}]},
        {"reverseOneToManyRels": [{"reverseManyToManyRels": [{"name": "2"}]}]},
        {"reverseOneToManyRels": [{"reverseManyToManyRels": [{"name": "3"}]}]},
    ]


###############################################################################################


def test_relations__reverse_many_to_many__forward_one_to_one(graphql_client):
    ExampleFactory.create(reverse_many_to_many_rels__forward_one_to_one_field__name="1")
    ExampleFactory.create(reverse_many_to_many_rels__forward_one_to_one_field__name="2")
    ExampleFactory.create(reverse_many_to_many_rels__forward_one_to_one_field__name="3")

    query = """
        query {
          examples {
            reverseManyToManyRels {
              forwardOneToOneField {
                name
              }
            }
          }
        }
    """

    response = graphql_client(query)
    assert response.no_errors, response.errors

    # 1 query for all examples
    # 1 query for all reverse many-to-many relations and nested forward one-to-one relations
    assert response.queries.count == 2, response.queries.log

    assert response.content == [
        {"reverseManyToManyRels": [{"forwardOneToOneField": {"name": "1"}}]},
        {"reverseManyToManyRels": [{"forwardOneToOneField": {"name": "2"}}]},
        {"reverseManyToManyRels": [{"forwardOneToOneField": {"name": "3"}}]},
    ]


def test_relations__reverse_many_to_many__forward_many_to_one(graphql_client):
    ExampleFactory.create(reverse_many_to_many_rels__forward_many_to_one_field__name="1")
    ExampleFactory.create(reverse_many_to_many_rels__forward_many_to_one_field__name="2")
    ExampleFactory.create(reverse_many_to_many_rels__forward_many_to_one_field__name="3")

    query = """
        query {
          examples {
            reverseManyToManyRels {
              forwardManyToOneField {
                name
              }
            }
          }
        }
    """

    response = graphql_client(query)
    assert response.no_errors, response.errors

    # 1 query for all examples
    # 1 query for all reverse many-to-many relations and nested forward many-to-one relations
    assert response.queries.count == 2, response.queries.log

    assert response.content == [
        {"reverseManyToManyRels": [{"forwardManyToOneField": {"name": "1"}}]},
        {"reverseManyToManyRels": [{"forwardManyToOneField": {"name": "2"}}]},
        {"reverseManyToManyRels": [{"forwardManyToOneField": {"name": "3"}}]},
    ]


def test_relations__reverse_many_to_many__forward_many_to_many(graphql_client):
    ExampleFactory.create(reverse_many_to_many_rels__forward_many_to_many_fields__name="1")
    ExampleFactory.create(reverse_many_to_many_rels__forward_many_to_many_fields__name="2")
    ExampleFactory.create(reverse_many_to_many_rels__forward_many_to_many_fields__name="3")

    query = """
        query {
          examples {
            reverseManyToManyRels {
              forwardManyToManyFields {
                name
              }
            }
          }
        }
    """

    response = graphql_client(query)
    assert response.no_errors, response.errors

    # 1 query for all examples
    # 1 query for all reverse many-to-many relations
    # 1 query for all nested forward many-to-many relations
    assert response.queries.count == 3, response.queries.log

    assert response.content == [
        {"reverseManyToManyRels": [{"forwardManyToManyFields": [{"name": "1"}]}]},
        {"reverseManyToManyRels": [{"forwardManyToManyFields": [{"name": "2"}]}]},
        {"reverseManyToManyRels": [{"forwardManyToManyFields": [{"name": "3"}]}]},
    ]


def test_relations__reverse_many_to_many__reverse_one_to_one(graphql_client):
    ExampleFactory.create(reverse_many_to_many_rels__reverse_one_to_one_rel__name="1")
    ExampleFactory.create(reverse_many_to_many_rels__reverse_one_to_one_rel__name="2")
    ExampleFactory.create(reverse_many_to_many_rels__reverse_one_to_one_rel__name="3")

    query = """
        query {
          examples {
            reverseManyToManyRels {
              reverseOneToOneRel {
                name
              }
            }
          }
        }
    """

    response = graphql_client(query)
    assert response.no_errors, response.errors

    # 1 query for all examples
    # 1 query for all reverse many-to-many relations and nested reverse one-to-one relations
    assert response.queries.count == 2, response.queries.log

    assert response.content == [
        {"reverseManyToManyRels": [{"reverseOneToOneRel": {"name": "1"}}]},
        {"reverseManyToManyRels": [{"reverseOneToOneRel": {"name": "2"}}]},
        {"reverseManyToManyRels": [{"reverseOneToOneRel": {"name": "3"}}]},
    ]


def test_relations__reverse_many_to_many__reverse_one_to_many(graphql_client):
    ExampleFactory.create(reverse_many_to_many_rels__reverse_one_to_many_rels__name="1")
    ExampleFactory.create(reverse_many_to_many_rels__reverse_one_to_many_rels__name="2")
    ExampleFactory.create(reverse_many_to_many_rels__reverse_one_to_many_rels__name="3")

    query = """
        query {
          examples {
            reverseManyToManyRels {
              reverseOneToManyRels {
                name
              }
            }
          }
        }
    """

    response = graphql_client(query)
    assert response.no_errors, response.errors

    # 1 query for all examples
    # 1 query for all reverse many-to-many relations
    # 1 query for all nested reverse one-to-many relations
    assert response.queries.count == 3, response.queries.log

    assert response.content == [
        {"reverseManyToManyRels": [{"reverseOneToManyRels": [{"name": "1"}]}]},
        {"reverseManyToManyRels": [{"reverseOneToManyRels": [{"name": "2"}]}]},
        {"reverseManyToManyRels": [{"reverseOneToManyRels": [{"name": "3"}]}]},
    ]


def test_relations__reverse_many_to_many__reverse_many_to_many(graphql_client):
    ExampleFactory.create(reverse_many_to_many_rels__reverse_many_to_many_rels__name="1")
    ExampleFactory.create(reverse_many_to_many_rels__reverse_many_to_many_rels__name="2")
    ExampleFactory.create(reverse_many_to_many_rels__reverse_many_to_many_rels__name="3")

    query = """
        query {
          examples {
            reverseManyToManyRels {
              reverseManyToManyRels {
                name
              }
            }
          }
        }
    """

    response = graphql_client(query)
    assert response.no_errors, response.errors

    # 1 query for all examples
    # 1 query for all reverse many-to-many relations
    # 1 query for all nested reverse many-to-many relations
    assert response.queries.count == 3, response.queries.log

    assert response.content == [
        {"reverseManyToManyRels": [{"reverseManyToManyRels": [{"name": "1"}]}]},
        {"reverseManyToManyRels": [{"reverseManyToManyRels": [{"name": "2"}]}]},
        {"reverseManyToManyRels": [{"reverseManyToManyRels": [{"name": "3"}]}]},
    ]
