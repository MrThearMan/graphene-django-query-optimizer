from __future__ import annotations

from typing import TYPE_CHECKING, Any

import graphene
import pytest

from example_project.undine_port.models import (
    Comment,
    Example,
    ExampleFFK,
    ExampleFMTM,
    ExampleFOTO,
    ExampleGeneric,
    ExampleRFK,
    ExampleRMTM,
    ExampleROTO,
    NestedExampleFFK,
    NestedExampleFMTM,
    NestedExampleFOTO,
    NestedExampleRFK,
    NestedExampleRMTM,
    NestedExampleROTO,
    Person,
    Project,
    Task,
    TaskTypeChoices,
    Team,
)
from query_optimizer import DjangoListField, DjangoObjectType
from tests.undine_port.factories import CommentFactory, PersonFactory, ProjectFactory, TaskFactory, TeamFactory
from tests.undine_port.factories.example import ExampleFactory

if TYPE_CHECKING:
    from django.db.models import Model

    from query_optimizer.typing import GQLInfo

###############################################################################################


def model_type(model: type[Model], **attrs: Any) -> type[DjangoObjectType]:
    """Create an object type with all model fields, like an Undine `QueryType` with no body."""
    meta = type("Meta", (), {"model": model, "fields": "__all__"})
    return type(f"{model.__name__}Type", (DjangoObjectType,), {"Meta": meta, **attrs})


def example_schema() -> graphene.Schema:
    def resolve_content_type(root: ExampleGeneric, info: GQLInfo) -> int:
        return root.content_type.pk

    model_type(ExampleGeneric, content_type=graphene.Int(resolver=resolve_content_type))

    example_type = model_type(Example)

    for model in (
        ExampleFOTO,
        ExampleFFK,
        ExampleFMTM,
        ExampleROTO,
        ExampleRFK,
        ExampleRMTM,
        NestedExampleFOTO,
        NestedExampleFFK,
        NestedExampleFMTM,
        NestedExampleROTO,
        NestedExampleRFK,
        NestedExampleRMTM,
    ):
        model_type(model)

    class Query(graphene.ObjectType):
        examples = DjangoListField(example_type)

    return graphene.Schema(query=Query)



@pytest.mark.django_db
def test_optimizer__relations__forward_one_to_one__forward_one_to_one(graphql) -> None:
    graphql.schema = example_schema()

    ExampleFactory.create(example_foto__example_foto__name="1")
    ExampleFactory.create(example_foto__example_foto__name="2")
    ExampleFactory.create(example_foto__example_foto__name="3")

    query = """
        query {
          examples {
            exampleFoto {
              exampleFoto {
                name
              }
            }
          }
        }
    """

    response = graphql(query, count_queries=True)
    assert response.has_errors is False, response.errors

    assert response.results == [
        {"exampleFoto": {"exampleFoto": {"name": "1"}}},
        {"exampleFoto": {"exampleFoto": {"name": "2"}}},
        {"exampleFoto": {"exampleFoto": {"name": "3"}}},
    ]

    response.assert_query_count(1)


@pytest.mark.django_db
def test_optimizer__relations__forward_one_to_one__forward_many_to_one(graphql) -> None:
    graphql.schema = example_schema()

    ExampleFactory.create(example_foto__example_ffk__name="1")
    ExampleFactory.create(example_foto__example_ffk__name="2")
    ExampleFactory.create(example_foto__example_ffk__name="3")

    query = """
        query {
          examples {
            exampleFoto {
              exampleFfk {
                name
              }
            }
          }
        }
    """

    response = graphql(query, count_queries=True)
    assert response.has_errors is False, response.errors

    assert response.results == [
        {"exampleFoto": {"exampleFfk": {"name": "1"}}},
        {"exampleFoto": {"exampleFfk": {"name": "2"}}},
        {"exampleFoto": {"exampleFfk": {"name": "3"}}},
    ]

    response.assert_query_count(1)


@pytest.mark.django_db
def test_optimizer__relations__forward_one_to_one__forward_many_to_many(graphql) -> None:
    graphql.schema = example_schema()

    ExampleFactory.create(example_foto__example_fmtm_set__name="1")
    ExampleFactory.create(example_foto__example_fmtm_set__name="2")
    ExampleFactory.create(example_foto__example_fmtm_set__name="3")

    query = """
        query {
          examples {
            exampleFoto {
              exampleFmtmSet {
                name
              }
            }
          }
        }
    """

    response = graphql(query, count_queries=True)
    assert response.has_errors is False, response.errors

    assert response.results == [
        {"exampleFoto": {"exampleFmtmSet": [{"name": "1"}]}},
        {"exampleFoto": {"exampleFmtmSet": [{"name": "2"}]}},
        {"exampleFoto": {"exampleFmtmSet": [{"name": "3"}]}},
    ]

    response.assert_query_count(2)


@pytest.mark.django_db
def test_optimizer__relations__forward_one_to_one__reverse_one_to_one(graphql) -> None:
    graphql.schema = example_schema()

    ExampleFactory.create(example_foto__example_roto__name="1")
    ExampleFactory.create(example_foto__example_roto__name="2")
    ExampleFactory.create(example_foto__example_roto__name="3")

    query = """
        query {
          examples {
            exampleFoto {
              exampleRoto {
                name
              }
            }
          }
        }
    """

    response = graphql(query, count_queries=True)
    assert response.has_errors is False, response.errors

    assert response.results == [
        {"exampleFoto": {"exampleRoto": {"name": "1"}}},
        {"exampleFoto": {"exampleRoto": {"name": "2"}}},
        {"exampleFoto": {"exampleRoto": {"name": "3"}}},
    ]

    response.assert_query_count(1)


@pytest.mark.django_db
def test_optimizer__relations__forward_one_to_one__reverse_one_to_many(graphql) -> None:
    graphql.schema = example_schema()

    ExampleFactory.create(example_foto__example_rfk_set__name="1")
    ExampleFactory.create(example_foto__example_rfk_set__name="2")
    ExampleFactory.create(example_foto__example_rfk_set__name="3")

    query = """
        query {
          examples {
            exampleFoto {
              exampleRfkSet {
                name
              }
            }
          }
        }
    """

    response = graphql(query, count_queries=True)
    assert response.has_errors is False, response.errors

    assert response.results == [
        {"exampleFoto": {"exampleRfkSet": [{"name": "1"}]}},
        {"exampleFoto": {"exampleRfkSet": [{"name": "2"}]}},
        {"exampleFoto": {"exampleRfkSet": [{"name": "3"}]}},
    ]

    response.assert_query_count(2)


@pytest.mark.django_db
def test_optimizer__relations__forward_one_to_one__reverse_many_to_many(graphql) -> None:
    graphql.schema = example_schema()

    ExampleFactory.create(example_foto__example_rmtm_set__name="1")
    ExampleFactory.create(example_foto__example_rmtm_set__name="2")
    ExampleFactory.create(example_foto__example_rmtm_set__name="3")

    query = """
        query {
          examples {
            exampleFoto {
              exampleRmtmSet {
                name
              }
            }
          }
        }
    """

    response = graphql(query, count_queries=True)
    assert response.has_errors is False, response.errors

    assert response.results == [
        {"exampleFoto": {"exampleRmtmSet": [{"name": "1"}]}},
        {"exampleFoto": {"exampleRmtmSet": [{"name": "2"}]}},
        {"exampleFoto": {"exampleRmtmSet": [{"name": "3"}]}},
    ]

    response.assert_query_count(2)


###############################################################################################


@pytest.mark.django_db
def test_optimizer__relations__forward_many_to_one__forward_one_to_one(graphql) -> None:
    graphql.schema = example_schema()

    ExampleFactory.create(example_ffk__example_foto__name="1")
    ExampleFactory.create(example_ffk__example_foto__name="2")
    ExampleFactory.create(example_ffk__example_foto__name="3")

    query = """
        query {
          examples {
            exampleFfk {
              exampleFoto {
                name
              }
            }
          }
        }
    """

    response = graphql(query, count_queries=True)
    assert response.has_errors is False, response.errors

    assert response.results == [
        {"exampleFfk": {"exampleFoto": {"name": "1"}}},
        {"exampleFfk": {"exampleFoto": {"name": "2"}}},
        {"exampleFfk": {"exampleFoto": {"name": "3"}}},
    ]

    response.assert_query_count(1)


@pytest.mark.django_db
def test_optimizer__relations__forward_many_to_one__forward_many_to_one(graphql) -> None:
    graphql.schema = example_schema()

    ExampleFactory.create(example_ffk__example_ffk__name="1")
    ExampleFactory.create(example_ffk__example_ffk__name="2")
    ExampleFactory.create(example_ffk__example_ffk__name="3")

    query = """
        query {
          examples {
            exampleFfk {
              exampleFfk {
                name
              }
            }
          }
        }
    """

    response = graphql(query, count_queries=True)
    assert response.has_errors is False, response.errors

    assert response.results == [
        {"exampleFfk": {"exampleFfk": {"name": "1"}}},
        {"exampleFfk": {"exampleFfk": {"name": "2"}}},
        {"exampleFfk": {"exampleFfk": {"name": "3"}}},
    ]

    response.assert_query_count(1)


@pytest.mark.django_db
def test_optimizer__relations__forward_many_to_one__forward_many_to_many(graphql) -> None:
    graphql.schema = example_schema()

    ExampleFactory.create(example_ffk__example_fmtm_set__name="1")
    ExampleFactory.create(example_ffk__example_fmtm_set__name="2")
    ExampleFactory.create(example_ffk__example_fmtm_set__name="3")

    query = """
        query {
          examples {
            exampleFfk {
              exampleFmtmSet {
                name
              }
            }
          }
        }
    """

    response = graphql(query, count_queries=True)
    assert response.has_errors is False, response.errors

    assert response.results == [
        {"exampleFfk": {"exampleFmtmSet": [{"name": "1"}]}},
        {"exampleFfk": {"exampleFmtmSet": [{"name": "2"}]}},
        {"exampleFfk": {"exampleFmtmSet": [{"name": "3"}]}},
    ]

    response.assert_query_count(2)


@pytest.mark.django_db
def test_optimizer__relations__forward_many_to_one__reverse_one_to_one(graphql) -> None:
    graphql.schema = example_schema()

    ExampleFactory.create(example_ffk__example_roto__name="1")
    ExampleFactory.create(example_ffk__example_roto__name="2")
    ExampleFactory.create(example_ffk__example_roto__name="3")

    query = """
        query {
          examples {
            exampleFfk {
              exampleRoto {
                name
              }
            }
          }
        }
    """

    response = graphql(query, count_queries=True)
    assert response.has_errors is False, response.errors

    assert response.results == [
        {"exampleFfk": {"exampleRoto": {"name": "1"}}},
        {"exampleFfk": {"exampleRoto": {"name": "2"}}},
        {"exampleFfk": {"exampleRoto": {"name": "3"}}},
    ]

    response.assert_query_count(1)


@pytest.mark.django_db
def test_optimizer__relations__forward_many_to_one__reverse_one_to_many(graphql) -> None:
    graphql.schema = example_schema()

    ExampleFactory.create(example_ffk__example_rfk_set__name="1")
    ExampleFactory.create(example_ffk__example_rfk_set__name="2")
    ExampleFactory.create(example_ffk__example_rfk_set__name="3")

    query = """
        query {
          examples {
            exampleFfk {
              exampleRfkSet {
                name
              }
            }
          }
        }
    """

    response = graphql(query, count_queries=True)
    assert response.has_errors is False, response.errors

    assert response.results == [
        {"exampleFfk": {"exampleRfkSet": [{"name": "1"}]}},
        {"exampleFfk": {"exampleRfkSet": [{"name": "2"}]}},
        {"exampleFfk": {"exampleRfkSet": [{"name": "3"}]}},
    ]

    response.assert_query_count(2)


@pytest.mark.django_db
def test_optimizer__relations__forward_many_to_one__reverse_many_to_many(graphql) -> None:
    graphql.schema = example_schema()

    ExampleFactory.create(example_ffk__example_rmtm_set__name="1")
    ExampleFactory.create(example_ffk__example_rmtm_set__name="2")
    ExampleFactory.create(example_ffk__example_rmtm_set__name="3")

    query = """
        query {
          examples {
            exampleFfk {
              exampleRmtmSet {
                name
              }
            }
          }
        }
    """

    response = graphql(query, count_queries=True)
    assert response.has_errors is False, response.errors

    assert response.results == [
        {"exampleFfk": {"exampleRmtmSet": [{"name": "1"}]}},
        {"exampleFfk": {"exampleRmtmSet": [{"name": "2"}]}},
        {"exampleFfk": {"exampleRmtmSet": [{"name": "3"}]}},
    ]

    response.assert_query_count(2)


###############################################################################################


@pytest.mark.django_db
def test_optimizer__relations__forward_many_to_many__forward_one_to_one(graphql) -> None:
    graphql.schema = example_schema()

    ExampleFactory.create(example_fmtm_set__example_foto__name="1")
    ExampleFactory.create(example_fmtm_set__example_foto__name="2")
    ExampleFactory.create(example_fmtm_set__example_foto__name="3")

    query = """
        query {
          examples {
            exampleFmtmSet {
              exampleFoto {
                name
              }
            }
          }
        }
    """

    response = graphql(query, count_queries=True)
    assert response.has_errors is False, response.errors

    assert response.results == [
        {"exampleFmtmSet": [{"exampleFoto": {"name": "1"}}]},
        {"exampleFmtmSet": [{"exampleFoto": {"name": "2"}}]},
        {"exampleFmtmSet": [{"exampleFoto": {"name": "3"}}]},
    ]

    response.assert_query_count(2)


@pytest.mark.django_db
def test_optimizer__relations__forward_many_to_many__forward_many_to_one(graphql) -> None:
    graphql.schema = example_schema()

    ExampleFactory.create(example_fmtm_set__example_ffk__name="1")
    ExampleFactory.create(example_fmtm_set__example_ffk__name="2")
    ExampleFactory.create(example_fmtm_set__example_ffk__name="3")

    query = """
        query {
          examples {
            exampleFmtmSet {
              exampleFfk {
                name
              }
            }
          }
        }
    """

    response = graphql(query, count_queries=True)
    assert response.has_errors is False, response.errors

    assert response.results == [
        {"exampleFmtmSet": [{"exampleFfk": {"name": "1"}}]},
        {"exampleFmtmSet": [{"exampleFfk": {"name": "2"}}]},
        {"exampleFmtmSet": [{"exampleFfk": {"name": "3"}}]},
    ]

    response.assert_query_count(2)


@pytest.mark.django_db
def test_optimizer__relations__forward_many_to_many__forward_many_to_many(graphql) -> None:
    graphql.schema = example_schema()

    ExampleFactory.create(example_fmtm_set__example_fmtm_set__name="1")
    ExampleFactory.create(example_fmtm_set__example_fmtm_set__name="2")
    ExampleFactory.create(example_fmtm_set__example_fmtm_set__name="3")

    query = """
        query {
          examples {
            exampleFmtmSet {
              exampleFmtmSet {
                name
              }
            }
          }
        }
    """

    response = graphql(query, count_queries=True)
    assert response.has_errors is False, response.errors

    assert response.results == [
        {"exampleFmtmSet": [{"exampleFmtmSet": [{"name": "1"}]}]},
        {"exampleFmtmSet": [{"exampleFmtmSet": [{"name": "2"}]}]},
        {"exampleFmtmSet": [{"exampleFmtmSet": [{"name": "3"}]}]},
    ]

    response.assert_query_count(3)


@pytest.mark.django_db
def test_optimizer__relations__forward_many_to_many__reverse_one_to_one(graphql) -> None:
    graphql.schema = example_schema()

    ExampleFactory.create(example_fmtm_set__example_roto__name="1")
    ExampleFactory.create(example_fmtm_set__example_roto__name="2")
    ExampleFactory.create(example_fmtm_set__example_roto__name="3")

    query = """
        query {
          examples {
            exampleFmtmSet {
              exampleRoto {
                name
              }
            }
          }
        }
    """

    response = graphql(query, count_queries=True)
    assert response.has_errors is False, response.errors

    assert response.results == [
        {"exampleFmtmSet": [{"exampleRoto": {"name": "1"}}]},
        {"exampleFmtmSet": [{"exampleRoto": {"name": "2"}}]},
        {"exampleFmtmSet": [{"exampleRoto": {"name": "3"}}]},
    ]

    response.assert_query_count(2)


@pytest.mark.django_db
def test_optimizer__relations__forward_many_to_many__reverse_one_to_many(graphql) -> None:
    graphql.schema = example_schema()

    ExampleFactory.create(example_fmtm_set__example_rfk_set__name="1")
    ExampleFactory.create(example_fmtm_set__example_rfk_set__name="2")
    ExampleFactory.create(example_fmtm_set__example_rfk_set__name="3")

    query = """
        query {
          examples {
            exampleFmtmSet {
              exampleRfkSet {
                name
              }
            }
          }
        }
    """

    response = graphql(query, count_queries=True)
    assert response.has_errors is False, response.errors

    assert response.results == [
        {"exampleFmtmSet": [{"exampleRfkSet": [{"name": "1"}]}]},
        {"exampleFmtmSet": [{"exampleRfkSet": [{"name": "2"}]}]},
        {"exampleFmtmSet": [{"exampleRfkSet": [{"name": "3"}]}]},
    ]

    response.assert_query_count(3)


@pytest.mark.django_db
def test_optimizer__relations__forward_many_to_many__reverse_many_to_many(graphql) -> None:
    graphql.schema = example_schema()

    ExampleFactory.create(example_fmtm_set__example_rmtm_set__name="1")
    ExampleFactory.create(example_fmtm_set__example_rmtm_set__name="2")
    ExampleFactory.create(example_fmtm_set__example_rmtm_set__name="3")

    query = """
        query {
          examples {
            exampleFmtmSet {
              exampleRmtmSet {
                name
              }
            }
          }
        }
    """

    response = graphql(query, count_queries=True)
    assert response.has_errors is False, response.errors

    assert response.results == [
        {"exampleFmtmSet": [{"exampleRmtmSet": [{"name": "1"}]}]},
        {"exampleFmtmSet": [{"exampleRmtmSet": [{"name": "2"}]}]},
        {"exampleFmtmSet": [{"exampleRmtmSet": [{"name": "3"}]}]},
    ]

    response.assert_query_count(3)


###############################################################################################


@pytest.mark.django_db
def test_optimizer__relations__reverse_one_to_one__forward_one_to_one(graphql) -> None:
    graphql.schema = example_schema()

    ExampleFactory.create(example_roto__example_foto__name="1")
    ExampleFactory.create(example_roto__example_foto__name="2")
    ExampleFactory.create(example_roto__example_foto__name="3")

    query = """
        query {
          examples {
            exampleRoto {
              exampleFoto {
                name
              }
            }
          }
        }
    """

    response = graphql(query, count_queries=True)
    assert response.has_errors is False, response.errors

    assert response.results == [
        {"exampleRoto": {"exampleFoto": {"name": "1"}}},
        {"exampleRoto": {"exampleFoto": {"name": "2"}}},
        {"exampleRoto": {"exampleFoto": {"name": "3"}}},
    ]

    response.assert_query_count(1)


@pytest.mark.django_db
def test_optimizer__relations__reverse_one_to_one__forward_many_to_one(graphql) -> None:
    graphql.schema = example_schema()

    ExampleFactory.create(example_roto__example_ffk__name="1")
    ExampleFactory.create(example_roto__example_ffk__name="2")
    ExampleFactory.create(example_roto__example_ffk__name="3")

    query = """
        query {
          examples {
            exampleRoto {
              exampleFfk {
                name
              }
            }
          }
        }
    """

    response = graphql(query, count_queries=True)
    assert response.has_errors is False, response.errors

    assert response.results == [
        {"exampleRoto": {"exampleFfk": {"name": "1"}}},
        {"exampleRoto": {"exampleFfk": {"name": "2"}}},
        {"exampleRoto": {"exampleFfk": {"name": "3"}}},
    ]

    response.assert_query_count(1)


@pytest.mark.django_db
def test_optimizer__relations__reverse_one_to_one__forward_many_to_many(graphql) -> None:
    graphql.schema = example_schema()

    ExampleFactory.create(example_roto__example_fmtm_set__name="1")
    ExampleFactory.create(example_roto__example_fmtm_set__name="2")
    ExampleFactory.create(example_roto__example_fmtm_set__name="3")

    query = """
        query {
          examples {
            exampleRoto {
              exampleFmtmSet {
                name
              }
            }
          }
        }
    """

    response = graphql(query, count_queries=True)
    assert response.has_errors is False, response.errors

    assert response.results == [
        {"exampleRoto": {"exampleFmtmSet": [{"name": "1"}]}},
        {"exampleRoto": {"exampleFmtmSet": [{"name": "2"}]}},
        {"exampleRoto": {"exampleFmtmSet": [{"name": "3"}]}},
    ]

    response.assert_query_count(2)


@pytest.mark.django_db
def test_optimizer__relations__reverse_one_to_one__reverse_one_to_one(graphql) -> None:
    graphql.schema = example_schema()

    ExampleFactory.create(example_roto__example_roto__name="1")
    ExampleFactory.create(example_roto__example_roto__name="2")
    ExampleFactory.create(example_roto__example_roto__name="3")

    query = """
        query {
          examples {
            exampleRoto {
              exampleRoto {
                name
              }
            }
          }
        }
    """

    response = graphql(query, count_queries=True)
    assert response.has_errors is False, response.errors

    assert response.results == [
        {"exampleRoto": {"exampleRoto": {"name": "1"}}},
        {"exampleRoto": {"exampleRoto": {"name": "2"}}},
        {"exampleRoto": {"exampleRoto": {"name": "3"}}},
    ]

    response.assert_query_count(1)


@pytest.mark.django_db
def test_optimizer__relations__reverse_one_to_one__reverse_one_to_many(graphql) -> None:
    graphql.schema = example_schema()

    ExampleFactory.create(example_roto__example_rfk_set__name="1")
    ExampleFactory.create(example_roto__example_rfk_set__name="2")
    ExampleFactory.create(example_roto__example_rfk_set__name="3")

    query = """
        query {
          examples {
            exampleRoto {
              exampleRfkSet {
                name
              }
            }
          }
        }
    """

    response = graphql(query, count_queries=True)
    assert response.has_errors is False, response.errors

    assert response.results == [
        {"exampleRoto": {"exampleRfkSet": [{"name": "1"}]}},
        {"exampleRoto": {"exampleRfkSet": [{"name": "2"}]}},
        {"exampleRoto": {"exampleRfkSet": [{"name": "3"}]}},
    ]

    response.assert_query_count(2)


@pytest.mark.django_db
def test_optimizer__relations__reverse_one_to_one__reverse_many_to_many(graphql) -> None:
    graphql.schema = example_schema()

    ExampleFactory.create(example_roto__example_rmtm_set__name="1")
    ExampleFactory.create(example_roto__example_rmtm_set__name="2")
    ExampleFactory.create(example_roto__example_rmtm_set__name="3")

    query = """
        query {
          examples {
            exampleRoto {
              exampleRmtmSet {
                name
              }
            }
          }
        }
    """

    response = graphql(query, count_queries=True)
    assert response.has_errors is False, response.errors

    assert response.results == [
        {"exampleRoto": {"exampleRmtmSet": [{"name": "1"}]}},
        {"exampleRoto": {"exampleRmtmSet": [{"name": "2"}]}},
        {"exampleRoto": {"exampleRmtmSet": [{"name": "3"}]}},
    ]

    response.assert_query_count(2)


###############################################################################################


@pytest.mark.django_db
def test_optimizer__relations__reverse_one_to_many__forward_one_to_one(graphql) -> None:
    graphql.schema = example_schema()

    ExampleFactory.create(example_rfk_set__example_foto__name="1")
    ExampleFactory.create(example_rfk_set__example_foto__name="2")
    ExampleFactory.create(example_rfk_set__example_foto__name="3")

    query = """
        query {
          examples {
            exampleRfkSet {
              exampleFoto {
                name
              }
            }
          }
        }
    """

    response = graphql(query, count_queries=True)
    assert response.has_errors is False, response.errors

    assert response.results == [
        {"exampleRfkSet": [{"exampleFoto": {"name": "1"}}]},
        {"exampleRfkSet": [{"exampleFoto": {"name": "2"}}]},
        {"exampleRfkSet": [{"exampleFoto": {"name": "3"}}]},
    ]

    response.assert_query_count(2)


@pytest.mark.django_db
def test_optimizer__relations__reverse_one_to_many__forward_many_to_one(graphql) -> None:
    graphql.schema = example_schema()

    ExampleFactory.create(example_rfk_set__example_ffk__name="1")
    ExampleFactory.create(example_rfk_set__example_ffk__name="2")
    ExampleFactory.create(example_rfk_set__example_ffk__name="3")

    query = """
        query {
          examples {
            exampleRfkSet {
              exampleFfk {
                name
              }
            }
          }
        }
    """

    response = graphql(query, count_queries=True)
    assert response.has_errors is False, response.errors

    assert response.results == [
        {"exampleRfkSet": [{"exampleFfk": {"name": "1"}}]},
        {"exampleRfkSet": [{"exampleFfk": {"name": "2"}}]},
        {"exampleRfkSet": [{"exampleFfk": {"name": "3"}}]},
    ]

    response.assert_query_count(2)


@pytest.mark.django_db
def test_optimizer__relations__reverse_one_to_many__forward_many_to_many(graphql) -> None:
    graphql.schema = example_schema()

    ExampleFactory.create(example_rfk_set__example_fmtm_set__name="1")
    ExampleFactory.create(example_rfk_set__example_fmtm_set__name="2")
    ExampleFactory.create(example_rfk_set__example_fmtm_set__name="3")

    query = """
        query {
          examples {
            exampleRfkSet {
              exampleFmtmSet {
                name
              }
            }
          }
        }
    """

    response = graphql(query, count_queries=True)
    assert response.has_errors is False, response.errors

    assert response.results == [
        {"exampleRfkSet": [{"exampleFmtmSet": [{"name": "1"}]}]},
        {"exampleRfkSet": [{"exampleFmtmSet": [{"name": "2"}]}]},
        {"exampleRfkSet": [{"exampleFmtmSet": [{"name": "3"}]}]},
    ]

    response.assert_query_count(3)


@pytest.mark.django_db
def test_optimizer__relations__reverse_one_to_many__reverse_one_to_one(graphql) -> None:
    graphql.schema = example_schema()

    ExampleFactory.create(example_rfk_set__example_roto__name="1")
    ExampleFactory.create(example_rfk_set__example_roto__name="2")
    ExampleFactory.create(example_rfk_set__example_roto__name="3")

    query = """
        query {
          examples {
            exampleRfkSet {
              exampleRoto {
                name
              }
            }
          }
        }
    """

    response = graphql(query, count_queries=True)
    assert response.has_errors is False, response.errors

    assert response.results == [
        {"exampleRfkSet": [{"exampleRoto": {"name": "1"}}]},
        {"exampleRfkSet": [{"exampleRoto": {"name": "2"}}]},
        {"exampleRfkSet": [{"exampleRoto": {"name": "3"}}]},
    ]

    response.assert_query_count(2)


@pytest.mark.django_db
def test_optimizer__relations__reverse_one_to_many__reverse_one_to_many(graphql) -> None:
    graphql.schema = example_schema()

    ExampleFactory.create(example_rfk_set__example_rfk_set__name="1")
    ExampleFactory.create(example_rfk_set__example_rfk_set__name="2")
    ExampleFactory.create(example_rfk_set__example_rfk_set__name="3")

    query = """
        query {
          examples {
            exampleRfkSet {
              exampleRfkSet {
                name
              }
            }
          }
        }
    """

    response = graphql(query, count_queries=True)
    assert response.has_errors is False, response.errors

    assert response.results == [
        {"exampleRfkSet": [{"exampleRfkSet": [{"name": "1"}]}]},
        {"exampleRfkSet": [{"exampleRfkSet": [{"name": "2"}]}]},
        {"exampleRfkSet": [{"exampleRfkSet": [{"name": "3"}]}]},
    ]

    response.assert_query_count(3)


@pytest.mark.django_db
def test_optimizer__relations__reverse_one_to_many__reverse_many_to_many(graphql) -> None:
    graphql.schema = example_schema()

    ExampleFactory.create(example_rfk_set__example_rmtm_set__name="1")
    ExampleFactory.create(example_rfk_set__example_rmtm_set__name="2")
    ExampleFactory.create(example_rfk_set__example_rmtm_set__name="3")

    query = """
        query {
          examples {
            exampleRfkSet {
              exampleRmtmSet {
                name
              }
            }
          }
        }
    """

    response = graphql(query, count_queries=True)
    assert response.has_errors is False, response.errors

    assert response.results == [
        {"exampleRfkSet": [{"exampleRmtmSet": [{"name": "1"}]}]},
        {"exampleRfkSet": [{"exampleRmtmSet": [{"name": "2"}]}]},
        {"exampleRfkSet": [{"exampleRmtmSet": [{"name": "3"}]}]},
    ]

    response.assert_query_count(3)


###############################################################################################


@pytest.mark.django_db
def test_optimizer__relations__reverse_many_to_many__forward_one_to_one(graphql) -> None:
    graphql.schema = example_schema()

    ExampleFactory.create(example_rmtm_set__example_foto__name="1")
    ExampleFactory.create(example_rmtm_set__example_foto__name="2")
    ExampleFactory.create(example_rmtm_set__example_foto__name="3")

    query = """
        query {
          examples {
            exampleRmtmSet {
              exampleFoto {
                name
              }
            }
          }
        }
    """

    response = graphql(query, count_queries=True)
    assert response.has_errors is False, response.errors

    assert response.results == [
        {"exampleRmtmSet": [{"exampleFoto": {"name": "1"}}]},
        {"exampleRmtmSet": [{"exampleFoto": {"name": "2"}}]},
        {"exampleRmtmSet": [{"exampleFoto": {"name": "3"}}]},
    ]

    response.assert_query_count(2)


@pytest.mark.django_db
def test_optimizer__relations__reverse_many_to_many__forward_many_to_one(graphql) -> None:
    graphql.schema = example_schema()

    ExampleFactory.create(example_rmtm_set__example_ffk__name="1")
    ExampleFactory.create(example_rmtm_set__example_ffk__name="2")
    ExampleFactory.create(example_rmtm_set__example_ffk__name="3")

    query = """
        query {
          examples {
            exampleRmtmSet {
              exampleFfk {
                name
              }
            }
          }
        }
    """

    response = graphql(query, count_queries=True)
    assert response.has_errors is False, response.errors

    assert response.results == [
        {"exampleRmtmSet": [{"exampleFfk": {"name": "1"}}]},
        {"exampleRmtmSet": [{"exampleFfk": {"name": "2"}}]},
        {"exampleRmtmSet": [{"exampleFfk": {"name": "3"}}]},
    ]

    response.assert_query_count(2)


@pytest.mark.django_db
def test_optimizer__relations__reverse_many_to_many__forward_many_to_many(graphql) -> None:
    graphql.schema = example_schema()

    ExampleFactory.create(example_rmtm_set__example_fmtm_set__name="1")
    ExampleFactory.create(example_rmtm_set__example_fmtm_set__name="2")
    ExampleFactory.create(example_rmtm_set__example_fmtm_set__name="3")

    query = """
        query {
          examples {
            exampleRmtmSet {
              exampleFmtmSet {
                name
              }
            }
          }
        }
    """

    response = graphql(query, count_queries=True)
    assert response.has_errors is False, response.errors

    assert response.results == [
        {"exampleRmtmSet": [{"exampleFmtmSet": [{"name": "1"}]}]},
        {"exampleRmtmSet": [{"exampleFmtmSet": [{"name": "2"}]}]},
        {"exampleRmtmSet": [{"exampleFmtmSet": [{"name": "3"}]}]},
    ]

    response.assert_query_count(3)


@pytest.mark.django_db
def test_optimizer__relations__reverse_many_to_many__reverse_one_to_one(graphql) -> None:
    graphql.schema = example_schema()

    ExampleFactory.create(example_rmtm_set__example_roto__name="1")
    ExampleFactory.create(example_rmtm_set__example_roto__name="2")
    ExampleFactory.create(example_rmtm_set__example_roto__name="3")

    query = """
        query {
          examples {
            exampleRmtmSet {
              exampleRoto {
                name
              }
            }
          }
        }
    """

    response = graphql(query, count_queries=True)
    assert response.has_errors is False, response.errors

    assert response.results == [
        {"exampleRmtmSet": [{"exampleRoto": {"name": "1"}}]},
        {"exampleRmtmSet": [{"exampleRoto": {"name": "2"}}]},
        {"exampleRmtmSet": [{"exampleRoto": {"name": "3"}}]},
    ]

    response.assert_query_count(2)


@pytest.mark.django_db
def test_optimizer__relations__reverse_many_to_many__reverse_one_to_many(graphql) -> None:
    graphql.schema = example_schema()

    ExampleFactory.create(example_rmtm_set__example_rfk_set__name="1")
    ExampleFactory.create(example_rmtm_set__example_rfk_set__name="2")
    ExampleFactory.create(example_rmtm_set__example_rfk_set__name="3")

    query = """
        query {
          examples {
            exampleRmtmSet {
              exampleRfkSet {
                name
              }
            }
          }
        }
    """

    response = graphql(query, count_queries=True)
    assert response.has_errors is False, response.errors

    assert response.results == [
        {"exampleRmtmSet": [{"exampleRfkSet": [{"name": "1"}]}]},
        {"exampleRmtmSet": [{"exampleRfkSet": [{"name": "2"}]}]},
        {"exampleRmtmSet": [{"exampleRfkSet": [{"name": "3"}]}]},
    ]

    response.assert_query_count(3)


@pytest.mark.django_db
def test_optimizer__relations__reverse_many_to_many__reverse_many_to_many(graphql) -> None:
    graphql.schema = example_schema()

    ExampleFactory.create(example_rmtm_set__example_rmtm_set__name="1")
    ExampleFactory.create(example_rmtm_set__example_rmtm_set__name="2")
    ExampleFactory.create(example_rmtm_set__example_rmtm_set__name="3")

    query = """
        query {
          examples {
            exampleRmtmSet {
              exampleRmtmSet {
                name
              }
            }
          }
        }
    """

    response = graphql(query, count_queries=True)
    assert response.has_errors is False, response.errors

    assert response.results == [
        {"exampleRmtmSet": [{"exampleRmtmSet": [{"name": "1"}]}]},
        {"exampleRmtmSet": [{"exampleRmtmSet": [{"name": "2"}]}]},
        {"exampleRmtmSet": [{"exampleRmtmSet": [{"name": "3"}]}]},
    ]

    response.assert_query_count(3)


###############################################################################################


def target_field(*target_types: type[DjangoObjectType]) -> graphene.Field:
    """A field for `Comment.target`. Undine creates a union for a generic foreign key automatically."""

    class CommentTarget(graphene.Union):
        class Meta:
            types = target_types

        @classmethod
        def resolve_type(cls, instance: Model, info: GQLInfo) -> type[DjangoObjectType]:
            return next(t for t in target_types if isinstance(instance, t._meta.model))

    def resolve_target(root: Comment, info: GQLInfo) -> Model | None:
        return root.target

    return graphene.Field(CommentTarget, resolver=resolve_target)


def comment_type(*target_types: type[DjangoObjectType]) -> type[DjangoObjectType]:
    class CommentType(DjangoObjectType):
        class Meta:
            model = Comment
            fields = ["contents", "commenter", "target"]

        target = target_field(*target_types)

    return CommentType


def simple_type(model: type[Model], fields: list[str], **attrs: Any) -> type[DjangoObjectType]:
    meta = type("Meta", (), {"model": model, "fields": fields})
    return type(f"{model.__name__}Type", (DjangoObjectType,), {"Meta": meta, **attrs})


def comments_schema(*target_types: type[DjangoObjectType]) -> graphene.Schema:
    class Query(graphene.ObjectType):
        comments = DjangoListField(comment_type(*target_types))

    return graphene.Schema(query=Query)


@pytest.mark.django_db
def test_optimizer__relations__generic_relation(graphql) -> None:
    comment = simple_type(Comment, ["contents"])
    task = simple_type(Task, ["comments"], comments=DjangoListField(comment))

    class Query(graphene.ObjectType):
        tasks = DjangoListField(task)

    graphql.schema = graphene.Schema(query=Query)

    task = TaskFactory.create()
    CommentFactory.create(contents="foo", target=task)
    CommentFactory.create(contents="bar", target=task)

    query = """
        query {
          tasks {
            comments {
              contents
            }
          }
        }
    """

    response = graphql(query, count_queries=True)
    assert response.has_errors is False, response.errors

    assert response.data == {
        "tasks": [
            {
                "comments": [
                    {"contents": "foo"},
                    {"contents": "bar"},
                ],
            },
        ],
    }

    response.assert_query_count(2)


@pytest.mark.django_db
def test_optimizer__relations__generic_foreign_key(graphql) -> None:
    graphql.schema = comments_schema(simple_type(Task, ["type"]), simple_type(Project, ["name"]))

    task = TaskFactory.create(type=TaskTypeChoices.STORY.value)
    project = ProjectFactory.create(name="project")
    CommentFactory.create(contents="foo", target=task)
    CommentFactory.create(contents="bar", target=project)

    query = """
        query {
          comments {
            target {
              ... on ProjectType {
                name
              }
              ... on TaskType {
                type
              }
            }
          }
        }
    """

    response = graphql(query, count_queries=True)
    assert response.has_errors is False, response.errors

    assert response.data == {
        "comments": [
            {
                "target": {"type": "STORY"},
            },
            {
                "target": {"name": "project"},
            },
        ],
    }

    response.assert_query_count(3)


@pytest.mark.django_db
def test_optimizer__relations__generic_foreign_key__as_nested_relation(graphql) -> None:
    comment = comment_type(simple_type(Task, ["type"]), simple_type(Project, ["name"]))
    person = simple_type(Person, ["name", "comments"], comments=DjangoListField(comment))

    class Query(graphene.ObjectType):
        people = DjangoListField(person)

    graphql.schema = graphene.Schema(query=Query)

    task = TaskFactory.create(type=TaskTypeChoices.TASK.value)
    project = ProjectFactory.create(name="Project 1")

    person_1 = PersonFactory.create(name="Person 1")
    person_2 = PersonFactory.create(name="Person 2")

    CommentFactory.create(contents="Comment 1", target=task, commenter=person_1)
    CommentFactory.create(contents="Comment 2", target=project, commenter=person_1)
    CommentFactory.create(contents="Comment 3", target=project, commenter=person_2)

    query = """
        query {
          people {
            name
            comments {
              contents
              target {
                ... on ProjectType {
                  name
                }
                ... on TaskType {
                  type
                }
              }
            }
          }
        }
    """

    response = graphql(query, count_queries=True)
    assert response.has_errors is False, response.errors

    assert response.data == {
        "people": [
            {
                "name": "Person 1",
                "comments": [
                    {
                        "contents": "Comment 1",
                        "target": {"type": "TASK"},
                    },
                    {
                        "contents": "Comment 2",
                        "target": {"name": "Project 1"},
                    },
                ],
            },
            {
                "name": "Person 2",
                "comments": [
                    {
                        "contents": "Comment 3",
                        "target": {"name": "Project 1"},
                    },
                ],
            },
        ],
    }

    response.assert_query_count(4)


@pytest.mark.django_db
@pytest.mark.xfail(
    reason=(
        "Generic foreign keys are prefetched with a plain lookup, so relations of the "
        "related models are not optimized (N+1 queries)."
    ),
    strict=True,
)
def test_optimizer__relations__generic_foreign_key__with_nested_relations(graphql) -> None:
    team = simple_type(Team, ["name"])
    project = simple_type(Project, ["name", "team"])
    task = simple_type(Task, ["type", "project"])
    graphql.schema = comments_schema(project, task)

    team = TeamFactory.create(name="team")
    project = ProjectFactory.create(name="project", team=team)
    task = TaskFactory.create(type=TaskTypeChoices.STORY.value, project=project)
    CommentFactory.create(contents="foo", target=task)
    CommentFactory.create(contents="bar", target=project)

    query = """
        query {
          comments {
            target {
              ... on ProjectType {
                name
                team {
                  name
                }
              }
              ... on TaskType {
                type
                project {
                  name
                }
              }
            }
          }
        }
    """

    response = graphql(query, count_queries=True)
    assert response.has_errors is False, response.errors

    assert response.data == {
        "comments": [
            {
                "target": {
                    "type": "STORY",
                    "project": {"name": "project"},
                },
            },
            {
                "target": {
                    "name": "project",
                    "team": {"name": "team"},
                },
            },
        ],
    }

    response.assert_query_count(3)


@pytest.mark.django_db
def test_optimizer__relations__generic_foreign_key__reuse_existing(graphql) -> None:
    graphql.schema = comments_schema(simple_type(Task, ["type"]))

    task = TaskFactory.create(type=TaskTypeChoices.BUG_FIX.value)
    CommentFactory.create(contents="c1", target=task)
    CommentFactory.create(contents="c2", target=task)

    query = """
        query {
          comments {
            target {
              ... on TaskType {
                type
              }
            }
          }
        }
    """

    response = graphql(query)
    assert response.has_errors is False, response.errors
    assert all(c["target"]["type"] == "BUG_FIX" for c in response.data["comments"])


@pytest.mark.django_db
def test_optimizer__relations__generic_foreign_key__skip_inline_fragment(graphql) -> None:
    graphql.schema = comments_schema(simple_type(Task, ["type"]))

    task = TaskFactory.create(type=TaskTypeChoices.STORY.value)
    CommentFactory.create(contents="c1", target=task)

    query = """
        query {
          comments {
            target {
              ... on TaskType @skip(if: true) {
                type
              }
            }
          }
        }
    """

    response = graphql(query)
    assert response.has_errors is False, response.errors


@pytest.mark.django_db
def test_optimizer__relations__generic_foreign_key__typename_field(graphql) -> None:
    graphql.schema = comments_schema(simple_type(Task, ["type"]))

    task = TaskFactory.create(type=TaskTypeChoices.TASK.value)
    CommentFactory.create(contents="c1", target=task)

    query = """
        query {
          comments {
            target {
              __typename
              ... on TaskType {
                type
              }
            }
          }
        }
    """

    response = graphql(query)
    assert response.has_errors is False, response.errors


@pytest.mark.django_db
@pytest.mark.xfail(
    reason="Inline fragment without a type condition crashes the optimizer (`type_condition` is `None`).",
    strict=True,
)
def test_optimizer__relations__generic_foreign_key__inline_fragment_no_type_condition(graphql) -> None:
    graphql.schema = comments_schema(simple_type(Task, ["type"]))

    task = TaskFactory.create(type=TaskTypeChoices.BUG_FIX.value)
    CommentFactory.create(contents="test", target=task)

    query = """
        query {
          comments {
            target {
              ... {
                __typename
              }
              ... on TaskType {
                type
              }
            }
          }
        }
    """

    response = graphql(query)
    assert response.has_errors is False, response.errors


@pytest.mark.skip(reason="No equivalent feature: generic prefetch with a custom `to_attr` per related model.")
def test_optimizer__relations__generic_foreign_key__custom_to_attr() -> None: ...


# Misc.


@pytest.mark.django_db
def test_optimizer__relations__same_relation_multiple_times(graphql) -> None:
    person = simple_type(Person, ["name", "email"])
    task = simple_type(Task, ["assignees"], assignees=DjangoListField(person))

    class Query(graphene.ObjectType):
        tasks = DjangoListField(task)

    graphql.schema = graphene.Schema(query=Query)

    person_1 = PersonFactory.create(name="foo", email="foo@example.com")
    person_2 = PersonFactory.create(name="bar", email="bar@example.com")
    TaskFactory.create(assignees=[person_1, person_2])

    query = """
        query {
          tasks {
            assignees {
              name
            }
            assignees {
              email
            }
          }
        }
    """

    response = graphql(query, count_queries=True)
    assert response.has_errors is False, response.errors

    assert response.data == {
        "tasks": [
            {
                "assignees": [
                    {"name": "foo", "email": "foo@example.com"},
                    {"name": "bar", "email": "bar@example.com"},
                ],
            },
        ],
    }

    response.assert_query_count(2)


@pytest.mark.django_db
def test_optimizer__relations__same_related_object_selected_with_different_fields(graphql) -> None:
    simple_type(Project, ["name", "tasks"])
    task = simple_type(Task, ["name", "type", "project"])

    class Query(graphene.ObjectType):
        tasks = DjangoListField(task)

    graphql.schema = graphene.Schema(query=Query)

    project = ProjectFactory.create(name="foo")
    TaskFactory.create(name="bar", type=TaskTypeChoices.BUG_FIX.value, project=project)

    # Test that both "type" and "name" are fetched for tasks in the same query,
    # since they belong to the same object.
    query = """
        query {
          tasks {
            type
            project {
              name
              tasks {
                name
              }
            }
          }
        }
    """

    response = graphql(query, count_queries=True)
    assert response.has_errors is False, response.errors

    assert response.data == {
        "tasks": [
            {
                "type": "BUG_FIX",
                "project": {
                    "name": "foo",
                    "tasks": [
                        {"name": "bar"},
                    ],
                },
            },
        ],
    }

    response.assert_query_count(2)


@pytest.mark.django_db
def test_optimizer__relations__related_objects_shared_by_multiple_objects(graphql) -> None:
    person = simple_type(Person, ["name"])
    simple_type(Project, ["name"])
    task = simple_type(Task, ["name", "project", "assignees"], assignees=DjangoListField(person))

    class Query(graphene.ObjectType):
        tasks = DjangoListField(task)

    graphql.schema = graphene.Schema(query=Query)

    person = PersonFactory.create(name="foo")
    project = ProjectFactory.create(name="bar")
    TaskFactory.create(name="bar", assignees=[person], project=project)
    TaskFactory.create(name="baz", assignees=[person], project=project)

    query = """
        query {
          tasks {
            name
            project {
              name
            }
            assignees {
              name
            }
          }
        }
    """

    response = graphql(query, count_queries=True)
    assert response.has_errors is False, response.errors

    assert response.data == {
        "tasks": [
            {
                "name": "bar",
                "project": {"name": "bar"},
                "assignees": [{"name": "foo"}],
            },
            {
                "name": "baz",
                "project": {"name": "bar"},
                "assignees": [{"name": "foo"}],
            },
        ],
    }

    response.assert_query_count(2)
