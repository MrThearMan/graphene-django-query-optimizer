from __future__ import annotations

import itertools
from typing import TYPE_CHECKING, Any

import graphene
import pytest
from graphene import relay

from example_project.undine_port.models import Project, Task, TaskTypeChoices
from query_optimizer import DjangoObjectType, optimize
from tests.undine_port.factories import ProjectFactory, TaskFactory

if TYPE_CHECKING:
    from django.db.models import Model

    from query_optimizer.typing import GQLInfo


# Undine `UnionType` entrypoints optimize each member model separately.
# Here, the union field resolver runs `optimize` for each member model, which results in one query per model.


def union_schema(*, project_fields: list[str], task_fields: list[str], connection: bool = False) -> graphene.Schema:
    class ProjectType(DjangoObjectType):
        class Meta:
            model = Project
            fields = project_fields

    class TaskType(DjangoObjectType):
        class Meta:
            model = Task
            fields = task_fields

    class Commentable(graphene.Union):
        class Meta:
            types = (TaskType, ProjectType)

        @classmethod
        def resolve_type(cls, instance: Model, info: GQLInfo) -> type[DjangoObjectType]:
            return ProjectType if isinstance(instance, Project) else TaskType

    def resolve_commentable(root: Any, info: GQLInfo, **kwargs: Any) -> list[Model]:
        projects = optimize(Project.objects.all(), info)
        tasks = optimize(Task.objects.all(), info)
        return list(itertools.chain(projects, tasks))

    if connection:

        class CommentableConnection(relay.Connection):
            class Meta:
                node = Commentable

            total_count = graphene.Int()

            def resolve_total_count(root: Any, info: GQLInfo) -> int:
                return len(root.iterable)

        class Query(graphene.ObjectType):
            commentable = relay.ConnectionField(CommentableConnection, resolver=resolve_commentable)

    else:

        class Query(graphene.ObjectType):  # type: ignore[no-redef]
            commentable = graphene.List(Commentable, resolver=resolve_commentable)

    return graphene.Schema(query=Query)


@pytest.mark.django_db
def test_optimizer__union(graphql) -> None:
    graphql.schema = union_schema(project_fields=["name"], task_fields=["type"])

    ProjectFactory.create(name="Project 1")
    ProjectFactory.create(name="Project 2")
    TaskFactory.create(name="Task 1", type=TaskTypeChoices.TASK)
    TaskFactory.create(name="Task 2", type=TaskTypeChoices.STORY)

    query = """
        query {
          commentable {
            ... on ProjectType {
              name
            }
            ... on TaskType {
              type
            }
          }
        }
    """

    response = graphql(query, count_queries=True)
    assert response.has_errors is False, response.errors

    assert response.data == {
        "commentable": [
            {"name": "Project 1"},
            {"name": "Project 2"},
            {"type": "TASK"},
            {"type": "STORY"},
        ]
    }

    response.assert_query_count(2)


@pytest.mark.django_db
def test_optimizer__union__only_one(graphql) -> None:
    graphql.schema = union_schema(project_fields=["name"], task_fields=["type"])

    ProjectFactory.create(name="Project 1")
    ProjectFactory.create(name="Project 2")
    TaskFactory.create(name="Task 1", type=TaskTypeChoices.TASK)
    TaskFactory.create(name="Task 2", type=TaskTypeChoices.STORY)

    query = """
        query {
          commentable {
            ... on ProjectType {
              name
            }
          }
        }
    """

    response = graphql(query, count_queries=True)
    assert response.has_errors is False, response.errors

    assert response.data == {
        "commentable": [
            {"name": "Project 1"},
            {"name": "Project 2"},
            {},
            {},
        ],
    }

    response.assert_query_count(2)


@pytest.mark.skip(reason="No equivalent feature: filtering union members with union field arguments.")
def test_optimizer__union__filtering() -> None: ...


@pytest.mark.skip(reason="No equivalent feature: ordering union members with union field arguments.")
def test_optimizer__union__ordering() -> None: ...


@pytest.mark.django_db
def test_optimizer__union__typename(graphql) -> None:
    graphql.schema = union_schema(project_fields=["name"], task_fields=["name"])

    ProjectFactory.create(name="Project 1")
    ProjectFactory.create(name="Project 2")
    TaskFactory.create(name="Task 1")
    TaskFactory.create(name="Task 2")

    query = """
        query {
          commentable {
            __typename
            ... on ProjectType {
              name
            }
            ... on TaskType {
              name
            }
          }
        }
    """

    response = graphql(query, count_queries=True)
    assert response.has_errors is False, response.errors

    assert response.data == {
        "commentable": [
            {"__typename": "ProjectType", "name": "Project 1"},
            {"__typename": "ProjectType", "name": "Project 2"},
            {"__typename": "TaskType", "name": "Task 1"},
            {"__typename": "TaskType", "name": "Task 2"},
        ]
    }

    response.assert_query_count(2)


@pytest.mark.django_db
def test_optimizer__union__connection(graphql) -> None:
    graphql.schema = union_schema(project_fields=["name"], task_fields=["type"], connection=True)

    ProjectFactory.create(name="Project 1")
    ProjectFactory.create(name="Project 2")
    TaskFactory.create(name="Task 1", type=TaskTypeChoices.TASK)
    TaskFactory.create(name="Task 2", type=TaskTypeChoices.STORY)

    query = """
        query {
          commentable {
            edges {
              node {
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

    assert response.edges == [
        {
            "node": {
                "name": "Project 1",
            },
        },
        {
            "node": {
                "name": "Project 2",
            },
        },
        {
            "node": {
                "type": "TASK",
            },
        },
        {
            "node": {
                "type": "STORY",
            },
        },
    ]

    response.assert_query_count(2)


@pytest.mark.django_db
def test_optimizer__union__connection__total_count(graphql) -> None:
    graphql.schema = union_schema(project_fields=["name"], task_fields=["type"], connection=True)

    ProjectFactory.create(name="Project 1")
    ProjectFactory.create(name="Project 2")
    TaskFactory.create(name="Task 1", type=TaskTypeChoices.TASK)
    TaskFactory.create(name="Task 2", type=TaskTypeChoices.STORY)

    query = """
        query {
          commentable {
            totalCount
            edges {
              node {
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

    assert response.results["totalCount"] == 4
    assert response.edges == [
        {
            "node": {
                "name": "Project 1",
            },
        },
        {
            "node": {
                "name": "Project 2",
            },
        },
        {
            "node": {
                "type": "TASK",
            },
        },
        {
            "node": {
                "type": "STORY",
            },
        },
    ]

    # Total count is calculated from the fetched items in the resolver, so no count queries are made.
    response.assert_query_count(2)


@pytest.mark.django_db
@pytest.mark.xfail(
    reason="Inline fragment without a type condition crashes the optimizer (`type_condition` is `None`).",
    strict=True,
)
def test_optimizer__union__inline_fragment_no_type_condition(graphql) -> None:
    """A fragment without a type condition passes its member fragments on to the union around it."""
    graphql.schema = union_schema(project_fields=["name"], task_fields=["type"])

    ProjectFactory.create(name="Project 1")
    TaskFactory.create(name="Task 1", type=TaskTypeChoices.TASK)

    query = """
        query {
          commentable {
            ... {
              ... on ProjectType {
                name
              }
            }
            ... on TaskType {
              type
            }
          }
        }
    """

    response = graphql(query, count_queries=True)
    assert response.has_errors is False, response.errors

    assert response.data == {
        "commentable": [
            {"name": "Project 1"},
            {"type": "TASK"},
        ]
    }

    response.assert_query_count(2)
