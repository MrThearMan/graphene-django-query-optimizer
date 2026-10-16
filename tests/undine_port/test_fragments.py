from __future__ import annotations

import itertools
from typing import TYPE_CHECKING, Any

import graphene
import pytest

from example_project.undine_port.models import Person, Project, Task, TaskTypeChoices
from query_optimizer import DjangoListField, DjangoObjectType, optimize
from tests.undine_port.factories import PersonFactory, ProjectFactory, TaskFactory

if TYPE_CHECKING:
    from collections.abc import Iterable

    from query_optimizer.typing import GQLInfo


def task_schema(*task_fields: str, **extra_fields: Any) -> graphene.Schema:
    class Meta:
        model = Task
        fields = list(task_fields)

    task_type = type("TaskType", (DjangoObjectType,), {"Meta": Meta, **extra_fields})

    class Query(graphene.ObjectType):
        tasks = DjangoListField(task_type)

    return graphene.Schema(query=Query)


@pytest.mark.django_db
@pytest.mark.xfail(
    reason="Inline fragment without a type condition crashes the optimizer (`type_condition` is `None`).",
    strict=True,
)
def test_optimizer__inline_fragment(graphql) -> None:
    graphql.schema = task_schema("name", "type")

    TaskFactory.create(name="foo", type=TaskTypeChoices.STORY)
    TaskFactory.create(name="bar", type=TaskTypeChoices.BUG_FIX)

    query = """
        query {
          tasks {
            name
            ... {
              type
            }
          }
        }
    """

    response = graphql(query, count_queries=True)
    assert response.has_errors is False, response.errors

    assert response.data == {
        "tasks": [
            {"name": "foo", "type": "STORY"},
            {"name": "bar", "type": "BUG_FIX"},
        ],
    }

    response.assert_query_count(1)


@pytest.mark.django_db
def test_optimizer__fragment_spread(graphql) -> None:
    graphql.schema = task_schema("type")

    TaskFactory.create(type=TaskTypeChoices.STORY)
    TaskFactory.create(type=TaskTypeChoices.BUG_FIX)

    query = """
        query {
          tasks {
            ...Type
          }
        }

        fragment Type on TaskType {
          type
        }
    """

    response = graphql(query, count_queries=True)
    assert response.has_errors is False, response.errors

    assert response.data == {
        "tasks": [
            {"type": "STORY"},
            {"type": "BUG_FIX"},
        ],
    }

    response.assert_query_count(1)


@pytest.mark.django_db
def test_optimizer__fragment_spread__query(graphql) -> None:
    graphql.schema = task_schema("type")

    TaskFactory.create(type=TaskTypeChoices.STORY)
    TaskFactory.create(type=TaskTypeChoices.BUG_FIX)

    query = """
        query {
          ...tasks
        }

        fragment tasks on Query {
          tasks {
            type
          }
        }
    """

    response = graphql(query, count_queries=True)
    assert response.has_errors is False, response.errors

    assert response.data == {
        "tasks": [
            {"type": "STORY"},
            {"type": "BUG_FIX"},
        ],
    }

    response.assert_query_count(1)


@pytest.mark.django_db
def test_optimizer__fragment_spread__to_one_relation(graphql) -> None:
    class ProjectType(DjangoObjectType):
        class Meta:
            model = Project
            fields = ["name"]

    graphql.schema = task_schema("project", project=graphene.Field(ProjectType))

    project = ProjectFactory.create(name="Foo")
    TaskFactory.create(project=project)

    query = """
        query {
          tasks {
            ...Project
          }
        }

        fragment Project on TaskType {
          project {
            name
          }
        }
    """

    response = graphql(query, count_queries=True)
    assert response.has_errors is False, response.errors

    assert response.data == {"tasks": [{"project": {"name": "Foo"}}]}

    response.assert_query_count(1)


@pytest.mark.django_db
def test_optimizer__fragment_spread__to_many_relation(graphql) -> None:
    class PersonType(DjangoObjectType):
        class Meta:
            model = Person
            fields = ["name"]

    graphql.schema = task_schema("assignees", assignees=DjangoListField(PersonType))

    person = PersonFactory.create(name="Foo")
    TaskFactory.create(assignees=[person])

    query = """
        query {
          tasks {
            ...Assignee
          }
        }

        fragment Assignee on TaskType {
          assignees {
            name
          }
        }
    """

    response = graphql(query, count_queries=True)
    assert response.has_errors is False, response.errors

    assert response.data == {"tasks": [{"assignees": [{"name": "Foo"}]}]}

    response.assert_query_count(2)


@pytest.mark.django_db
def test_optimizer__fragment_spread__same_relation_in_multiple_fragments(graphql) -> None:
    class PersonType(DjangoObjectType):
        class Meta:
            model = Person
            fields = ["name", "email"]

    graphql.schema = task_schema("assignees", assignees=DjangoListField(PersonType))

    person = PersonFactory.create(name="Foo", email="foo@example.org")
    TaskFactory.create(assignees=[person])

    query = """
        query {
          tasks {
            ...Name
            ...Email
          }
        }

        fragment Name on TaskType {
          assignees {
            name
          }
        }

        fragment Email on TaskType {
          assignees {
            email
          }
        }
    """

    response = graphql(query, count_queries=True)
    assert response.has_errors is False, response.errors

    assert response.data == {
        "tasks": [
            {
                "assignees": [
                    {"name": "Foo", "email": "foo@example.org"},
                ],
            },
        ],
    }

    response.assert_query_count(2)


@pytest.mark.django_db
def test_ast_walker__fragment_spread__flatten_abstract_type_selections(graphql) -> None:
    class Named(graphene.Interface):
        name = graphene.String(required=True)

    class TaskType(DjangoObjectType):
        class Meta:
            model = Task
            fields = ["name", "type"]
            interfaces = (Named,)

    class ProjectType(DjangoObjectType):
        class Meta:
            model = Project
            fields = ["name"]
            interfaces = (Named,)

    class Query(graphene.ObjectType):
        named = graphene.List(Named)
        tasks = DjangoListField(TaskType)
        projects = DjangoListField(ProjectType)

        def resolve_named(root: Any, info: GQLInfo) -> Iterable[Task | Project]:
            tasks = optimize(Task.objects.all(), info)
            projects = optimize(Project.objects.all(), info)
            return itertools.chain(tasks, projects)

    graphql.schema = graphene.Schema(query=Query)

    TaskFactory.create(name="T1", type=TaskTypeChoices.TASK)
    ProjectFactory.create(name="P1")

    query = """
        query {
          named {
            ...NamedFragment
          }
        }

        fragment NamedFragment on Named {
          ... on TaskType {
            type
          }
          ... on ProjectType {
            name
          }
        }
    """

    response = graphql(query)

    assert response.has_errors is False, response.errors
    assert len(response.data["named"]) == 2
