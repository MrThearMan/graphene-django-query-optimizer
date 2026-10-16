from __future__ import annotations

import graphene
import pytest

from example_project.undine_port.models import Task
from query_optimizer import DjangoListField, DjangoObjectType
from tests.undine_port.factories import TaskFactory


def task_schema() -> graphene.Schema:
    class TaskType(DjangoObjectType):
        class Meta:
            model = Task
            fields = ["name", "done"]

    class Query(graphene.ObjectType):
        tasks = DjangoListField(TaskType)

    return graphene.Schema(query=Query)


@pytest.mark.django_db
@pytest.mark.xfail(reason="Optimizer ignores @skip/@include and fetches skipped fields.", strict=True)
def test_optimizer__directives__include__false(graphql) -> None:
    graphql.schema = task_schema()

    TaskFactory.create(name="foo", done=True)

    query = """
        query {
          tasks {
            name @include(if: false)
            done
          }
        }
    """

    response = graphql(query, count_queries=True)
    assert response.has_errors is False, response.errors

    assert response.data == {"tasks": [{"done": True}]}

    assert len(response.queries) == 1
    assert "name" not in response.queries[0]


@pytest.mark.django_db
def test_optimizer__directives__include__true(graphql) -> None:
    graphql.schema = task_schema()

    TaskFactory.create(name="foo", done=True)

    query = """
        query {
          tasks {
            name @include(if: true)
            done
          }
        }
    """

    response = graphql(query, count_queries=True)
    assert response.has_errors is False, response.errors

    assert response.data == {"tasks": [{"name": "foo", "done": True}]}

    assert len(response.queries) == 1
    assert "name" in response.queries[0]


@pytest.mark.django_db
def test_optimizer__directives__skip__false(graphql) -> None:
    graphql.schema = task_schema()

    TaskFactory.create(name="foo", done=True)

    query = """
        query {
          tasks {
            name @skip(if: false)
            done
          }
        }
    """

    response = graphql(query, count_queries=True)
    assert response.has_errors is False, response.errors

    assert response.data == {"tasks": [{"name": "foo", "done": True}]}

    assert len(response.queries) == 1
    assert "name" in response.queries[0]


@pytest.mark.django_db
@pytest.mark.xfail(reason="Optimizer ignores @skip/@include and fetches skipped fields.", strict=True)
def test_optimizer__directives__skip__true(graphql) -> None:
    graphql.schema = task_schema()

    TaskFactory.create(name="foo", done=True)

    query = """
        query {
          tasks {
            name @skip(if: true)
            done
          }
        }
    """

    response = graphql(query, count_queries=True)
    assert response.has_errors is False, response.errors

    assert response.data == {"tasks": [{"done": True}]}

    assert len(response.queries) == 1
    assert "name" not in response.queries[0]
