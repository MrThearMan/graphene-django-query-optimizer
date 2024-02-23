import json

import pytest

from tests.example.utils import capture_database_queries

pytestmark = pytest.mark.django_db

###############################################################################################


def test_optimizer__forward_one_to_one__forward_one_to_one(client_query):
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

    with capture_database_queries() as results:
        response = client_query(query)

    content = json.loads(response.content)
    assert "errors" not in content, content["errors"]

    # 1 query for all examples, forward one-to-one relations, and nested forward one-to-one relations
    assert results.query_count == 1, results.log


def test_optimizer__forward_one_to_one__forward_many_to_one(client_query):
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

    with capture_database_queries() as results:
        response = client_query(query)

    content = json.loads(response.content)
    assert "errors" not in content, content["errors"]

    # 1 query for all examples, forward one-to-one relations, and nested forward many-to-one relations
    assert results.query_count == 1, results.log


def test_optimizer__forward_one_to_one__forward_many_to_many(client_query):
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

    with capture_database_queries() as results:
        response = client_query(query)

    content = json.loads(response.content)
    assert "errors" not in content, content["errors"]

    # 1 query for all examples, forward one-to-one relations
    # 1 query for all nested forward many-to-many relations
    assert results.query_count == 2, results.log


def test_optimizer__forward_one_to_one__reverse_one_to_one(client_query):
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

    with capture_database_queries() as results:
        response = client_query(query)

    content = json.loads(response.content)
    assert "errors" not in content, content["errors"]

    # 1 query for all examples, forward one-to-one relations and nested reverse one-to-one relations
    assert results.query_count == 1, results.log


def test_optimizer__forward_one_to_one__reverse_one_to_many(client_query):
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

    with capture_database_queries() as results:
        response = client_query(query)

    content = json.loads(response.content)
    assert "errors" not in content, content["errors"]

    # 1 query for all examples, forward one-to-one relations
    # 1 query for all nested reverse one-to-many relations
    assert results.query_count == 2, results.log


def test_optimizer__forward_one_to_one__reverse_many_to_many(client_query):
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

    with capture_database_queries() as results:
        response = client_query(query)

    content = json.loads(response.content)
    assert "errors" not in content, content["errors"]

    # 1 query for all examples, forward one-to-one relations
    # 1 query for all nested reverse many-to-many relations
    assert results.query_count == 2, results.log


###############################################################################################


def test_optimizer__forward_many_to_one__forward_one_to_one(client_query):
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

    with capture_database_queries() as results:
        response = client_query(query)

    content = json.loads(response.content)
    assert "errors" not in content, content["errors"]

    # 1 query for all examples, forward many-to-one relations, and nested forward one-to-one relations
    assert results.query_count == 1, results.log


def test_optimizer__forward_many_to_one__forward_many_to_one(client_query):
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

    with capture_database_queries() as results:
        response = client_query(query)

    content = json.loads(response.content)
    assert "errors" not in content, content["errors"]

    # 1 query for all examples, forward many-to-one relations, and nested forward many-to-one relations
    assert results.query_count == 1, results.log


def test_optimizer__forward_many_to_one__forward_many_to_many(client_query):
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

    with capture_database_queries() as results:
        response = client_query(query)

    content = json.loads(response.content)
    assert "errors" not in content, content["errors"]

    # 1 query for all examples, forward many-to-one relations
    # 1 query for all nested forward many-to-many relations
    assert results.query_count == 2, results.log


def test_optimizer__forward_many_to_one__reverse_one_to_one(client_query):
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

    with capture_database_queries() as results:
        response = client_query(query)

    content = json.loads(response.content)
    assert "errors" not in content, content["errors"]

    # 1 query for all examples, forward many-to-one relations and nested reverse one-to-one relations
    assert results.query_count == 1, results.log


def test_optimizer__forward_many_to_one__reverse_one_to_many(client_query):
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

    with capture_database_queries() as results:
        response = client_query(query)

    content = json.loads(response.content)
    assert "errors" not in content, content["errors"]

    # 1 query for all examples, forward many-to-one relations
    # 1 query for all nested reverse one-to-many relations
    assert results.query_count == 2, results.log


def test_optimizer__forward_many_to_one__reverse_many_to_many(client_query):
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

    with capture_database_queries() as results:
        response = client_query(query)

    content = json.loads(response.content)
    assert "errors" not in content, content["errors"]

    # 1 query for all examples, forward many-to-one relations
    # 1 query for all nested reverse many-to-many relations
    assert results.query_count == 2, results.log


###############################################################################################


def test_optimizer__forward_many_to_many__forward_one_to_one(client_query):
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

    with capture_database_queries() as results:
        response = client_query(query)

    content = json.loads(response.content)
    assert "errors" not in content, content["errors"]

    # 1 query for all examples
    # 1 query fo all forward many-to-many relations, and nested forward one-to-one relations
    assert results.query_count == 2, results.log


def test_optimizer__forward_many_to_many__forward_many_to_one(client_query):
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

    with capture_database_queries() as results:
        response = client_query(query)

    content = json.loads(response.content)
    assert "errors" not in content, content["errors"]

    # 1 query for all examples
    # 1 query fo all forward many-to-many relations, and nested forward many-to-one relations
    assert results.query_count == 2, results.log


def test_optimizer__forward_many_to_many__forward_many_to_many(client_query):
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

    with capture_database_queries() as results:
        response = client_query(query)

    content = json.loads(response.content)
    assert "errors" not in content, content["errors"]

    # 1 query for all examples
    # 1 query fo all forward many-to-many relations
    # 1 query for all nested forward many-to-many relations
    assert results.query_count == 3, results.log


def test_optimizer__forward_many_to_many__reverse_one_to_one(client_query):
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

    with capture_database_queries() as results:
        response = client_query(query)

    content = json.loads(response.content)
    assert "errors" not in content, content["errors"]

    # 1 query for all examples
    # 1 query for all forward many-to-many relations and nested reverse one-to-one relations
    assert results.query_count == 2, results.log


def test_optimizer__forward_many_to_many__reverse_one_to_many(client_query):
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

    with capture_database_queries() as results:
        response = client_query(query)

    content = json.loads(response.content)
    assert "errors" not in content, content["errors"]

    # 1 query for all examples
    # 1 query for all forward many-to-many relations
    # 1 query for all nested reverse one-to-many relations
    assert results.query_count == 3, results.log


def test_optimizer__forward_many_to_many__reverse_many_to_many(client_query):
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

    with capture_database_queries() as results:
        response = client_query(query)

    content = json.loads(response.content)
    assert "errors" not in content, content["errors"]

    # 1 query for all examples
    # 1 query for all forward many-to-many relations
    # 1 query for all nested reverse many-to-many relations
    assert results.query_count == 3, results.log


###############################################################################################


def test_optimizer__reverse_one_to_one__forward_one_to_one(client_query):
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

    with capture_database_queries() as results:
        response = client_query(query)

    content = json.loads(response.content)
    assert "errors" not in content, content["errors"]

    # 1 query for all examples, reverse one-to-one relations, and nested forward one-to-one relations
    assert results.query_count == 1, results.log


def test_optimizer__reverse_one_to_one__forward_many_to_one(client_query):
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

    with capture_database_queries() as results:
        response = client_query(query)

    content = json.loads(response.content)
    assert "errors" not in content, content["errors"]

    # 1 query for all examples, reverse one-to-one relations, and nested forward many-to-one relations
    assert results.query_count == 1, results.log


def test_optimizer__reverse_one_to_one__forward_many_to_many(client_query):
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

    with capture_database_queries() as results:
        response = client_query(query)

    content = json.loads(response.content)
    assert "errors" not in content, content["errors"]

    # 1 query for all examples, reverse one-to-one relations
    # 1 query for all nested forward many-to-many relations
    assert results.query_count == 2, results.log


def test_optimizer__reverse_one_to_one__reverse_one_to_one(client_query):
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

    with capture_database_queries() as results:
        response = client_query(query)

    content = json.loads(response.content)
    assert "errors" not in content, content["errors"]

    # 1 query for all examples, reverse one-to-one relations and nested reverse one-to-one relations
    assert results.query_count == 1, results.log


def test_optimizer__reverse_one_to_one__reverse_one_to_many(client_query):
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

    with capture_database_queries() as results:
        response = client_query(query)

    content = json.loads(response.content)
    assert "errors" not in content, content["errors"]

    # 1 query for all examples, reverse one-to-one relations
    # 1 query for all nested reverse one-to-many relations
    assert results.query_count == 2, results.log


def test_optimizer__reverse_one_to_one__reverse_many_to_many(client_query):
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

    with capture_database_queries() as results:
        response = client_query(query)

    content = json.loads(response.content)
    assert "errors" not in content, content["errors"]

    # 1 query for all examples, reverse one-to-one relations
    # 1 query for all nested reverse many-to-many relations
    assert results.query_count == 2, results.log


###############################################################################################


def test_optimizer__reverse_one_to_many__forward_one_to_one(client_query):
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

    with capture_database_queries() as results:
        response = client_query(query)

    content = json.loads(response.content)
    assert "errors" not in content, content["errors"]

    # 1 query for all examples
    # 1 query for all reverse one-to-many relations query and nested forward one-to-one relations
    assert results.query_count == 2, results.log


def test_optimizer__reverse_one_to_many__forward_many_to_one(client_query):
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

    with capture_database_queries() as results:
        response = client_query(query)

    content = json.loads(response.content)
    assert "errors" not in content, content["errors"]

    # 1 query for all examples
    # 1 query for all reverse one-to-many relations query and nested forward many-to-one relations
    assert results.query_count == 2, results.log


def test_optimizer__reverse_one_to_many__forward_many_to_many(client_query):
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

    with capture_database_queries() as results:
        response = client_query(query)

    content = json.loads(response.content)
    assert "errors" not in content, content["errors"]

    # 1 query for all examples
    # 1 query for all reverse one-to-many relations
    # 1 query for all nested forward many-to-many relations
    assert results.query_count == 3, results.log


def test_optimizer__reverse_one_to_many__reverse_one_to_one(client_query):
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

    with capture_database_queries() as results:
        response = client_query(query)

    content = json.loads(response.content)
    assert "errors" not in content, content["errors"]

    # 1 query for all examples
    # 1 query for all reverse one-to-many relations query and nested reverse one-to-one relations
    assert results.query_count == 2, results.log


def test_optimizer__reverse_one_to_many__reverse_one_to_many(client_query):
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

    with capture_database_queries() as results:
        response = client_query(query)

    content = json.loads(response.content)
    assert "errors" not in content, content["errors"]

    # 1 query for all examples
    # 1 query for all reverse one-to-many relations
    # 1 query for all nested reverse one-to-many relations
    assert results.query_count == 3, results.log


def test_optimizer__reverse_one_to_many__reverse_many_to_many(client_query):
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

    with capture_database_queries() as results:
        response = client_query(query)

    content = json.loads(response.content)
    assert "errors" not in content, content["errors"]

    # 1 query for all examples
    # 1 query for all reverse one-to-many relations
    # 1 query for all nested reverse many-to-many relations
    assert results.query_count == 3, results.log


###############################################################################################


def test_optimizer__reverse_many_to_many__forward_one_to_one(client_query):
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

    with capture_database_queries() as results:
        response = client_query(query)

    content = json.loads(response.content)
    assert "errors" not in content, content["errors"]

    # 1 query for all examples
    # 1 query for all reverse many-to-many relations and nested forward one-to-one relations
    assert results.query_count == 2, results.log


def test_optimizer__reverse_many_to_many__forward_many_to_one(client_query):
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

    with capture_database_queries() as results:
        response = client_query(query)

    content = json.loads(response.content)
    assert "errors" not in content, content["errors"]

    # 1 query for all examples
    # 1 query for all reverse many-to-many relations and nested forward many-to-one relations
    assert results.query_count == 2, results.log


def test_optimizer__reverse_many_to_many__forward_many_to_many(client_query):
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

    with capture_database_queries() as results:
        response = client_query(query)

    content = json.loads(response.content)
    assert "errors" not in content, content["errors"]

    # 1 query for all examples
    # 1 query for all reverse many-to-many relations
    # 1 query for all nested forward many-to-many relations
    assert results.query_count == 3, results.log


def test_optimizer__reverse_many_to_many__reverse_one_to_one(client_query):
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

    with capture_database_queries() as results:
        response = client_query(query)

    content = json.loads(response.content)
    assert "errors" not in content, content["errors"]

    # 1 query for all examples
    # 1 query for all reverse many-to-many relations and nested reverse one-to-one relations
    assert results.query_count == 2, results.log


def test_optimizer__reverse_many_to_many__reverse_one_to_many(client_query):
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

    with capture_database_queries() as results:
        response = client_query(query)

    content = json.loads(response.content)
    assert "errors" not in content, content["errors"]

    # 1 query for all examples
    # 1 query for all reverse many-to-many relations
    # 1 query for all nested reverse one-to-many relations
    assert results.query_count == 3, results.log


def test_optimizer__reverse_many_to_many__reverse_many_to_many(client_query):
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

    with capture_database_queries() as results:
        response = client_query(query)

    content = json.loads(response.content)
    assert "errors" not in content, content["errors"]

    # 1 query for all examples
    # 1 query for all reverse many-to-many relations
    # 1 query for all nested reverse many-to-many relations
    assert results.query_count == 3, results.log
