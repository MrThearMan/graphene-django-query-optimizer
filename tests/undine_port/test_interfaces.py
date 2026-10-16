from __future__ import annotations

import itertools
from typing import TYPE_CHECKING, Any

import graphene
import pytest

from example_project.undine_port.models import Project, Task, TaskTypeChoices
from query_optimizer import DjangoListField, DjangoObjectType, optimize
from tests.undine_port.factories import ProjectFactory, TaskFactory

if TYPE_CHECKING:
    from django.db.models import Model

    from query_optimizer.typing import GQLInfo


# Undine `InterfaceType` entrypoints optimize each implementing model separately.
# Here, the interface field resolver runs `optimize` for each implementing model,
# which results in one query per model.


def interface_schema(*, with_id: bool = False) -> graphene.Schema:
    class Named(graphene.Interface):
        name = graphene.String(required=True)

        if with_id:
            id = graphene.Int(required=True)

    class ProjectType(DjangoObjectType):
        class Meta:
            model = Project
            fields = ["pk", "name", "id"]
            interfaces = (Named,)

    class TaskType(DjangoObjectType):
        class Meta:
            model = Task
            fields = ["type", "name", "id"]
            interfaces = (Named,)

    class Query(graphene.ObjectType):
        named = graphene.List(Named)

        tasks = DjangoListField(TaskType)
        projects = DjangoListField(ProjectType)

        def resolve_named(root: Any, info: GQLInfo) -> list[Model]:
            projects = optimize(Project.objects.all(), info)
            tasks = optimize(Task.objects.all(), info)
            return list(itertools.chain(projects, tasks))

    return graphene.Schema(query=Query)


@pytest.mark.django_db
@pytest.mark.xfail(
    reason="Selecting a field (also `__typename`) directly on a `graphene.Interface` crashes the optimizer (unhandled graphene type).",
    strict=True,
)
def test_optimizer__interfaces(graphql) -> None:
    graphql.schema = interface_schema()

    project_1 = ProjectFactory.create(name="Project 1")
    project_2 = ProjectFactory.create(name="Project 2")
    task_1 = TaskFactory.create(name="Task 1", type=TaskTypeChoices.TASK)
    task_2 = TaskFactory.create(name="Task 2", type=TaskTypeChoices.STORY)

    query = """
        query {
          named {
            name
            ... on ProjectType {
              pk
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
        "named": [
            {"pk": project_1.pk, "name": "Project 1"},
            {"pk": project_2.pk, "name": "Project 2"},
            {"name": "Task 1", "type": "TASK"},
            {"name": "Task 2", "type": "STORY"},
        ]
    }

    response.assert_query_count(2)


@pytest.mark.django_db
@pytest.mark.xfail(
    reason="Selecting a field (also `__typename`) directly on a `graphene.Interface` crashes the optimizer (unhandled graphene type).",
    strict=True,
)
def test_optimizer__interfaces__only_one_fragment(graphql) -> None:
    graphql.schema = interface_schema()

    project_1 = ProjectFactory.create(name="Project 1")
    project_2 = ProjectFactory.create(name="Project 2")
    task_1 = TaskFactory.create(name="Task 1", type=TaskTypeChoices.TASK)
    task_2 = TaskFactory.create(name="Task 2", type=TaskTypeChoices.STORY)

    query = """
        query {
          named {
            name
            ... on TaskType {
              type
            }
          }
        }
    """

    response = graphql(query, count_queries=True)

    assert response.has_errors is False, response.errors

    assert response.data == {
        "named": [
            {"name": "Project 1"},
            {"name": "Project 2"},
            {"name": "Task 1", "type": "TASK"},
            {"name": "Task 2", "type": "STORY"},
        ]
    }

    response.assert_query_count(2)


@pytest.mark.django_db
@pytest.mark.xfail(
    reason="Selecting a field (also `__typename`) directly on a `graphene.Interface` crashes the optimizer (unhandled graphene type).",
    strict=True,
)
def test_optimizer__interfaces__only_interface_fields(graphql) -> None:
    graphql.schema = interface_schema()

    project_1 = ProjectFactory.create(name="Project 1")
    project_2 = ProjectFactory.create(name="Project 2")
    task_1 = TaskFactory.create(name="Task 1", type=TaskTypeChoices.TASK)
    task_2 = TaskFactory.create(name="Task 2", type=TaskTypeChoices.STORY)

    query = """
        query {
          named {
            name
          }
        }
    """

    response = graphql(query, count_queries=True)

    assert response.has_errors is False, response.errors

    assert response.data == {
        "named": [{"name": "Project 1"}, {"name": "Project 2"}, {"name": "Task 1"}, {"name": "Task 2"}]
    }

    response.assert_query_count(2)


@pytest.mark.django_db
def test_optimizer__interfaces__only_fragment_fields(graphql) -> None:
    graphql.schema = interface_schema()

    project_1 = ProjectFactory.create(name="Project 1")
    project_2 = ProjectFactory.create(name="Project 2")
    task_1 = TaskFactory.create(name="Task 1", type=TaskTypeChoices.TASK)
    task_2 = TaskFactory.create(name="Task 2", type=TaskTypeChoices.STORY)

    query = """
        query {
          named {
            ... on ProjectType {
              pk
            }
            ... on TaskType {
              type
            }
          }
        }
    """

    response = graphql(query, count_queries=True)

    assert response.has_errors is False, response.errors

    assert response.data == {"named": [{"pk": project_1.pk}, {"pk": project_2.pk}, {"type": "TASK"}, {"type": "STORY"}]}

    response.assert_query_count(2)


@pytest.mark.django_db
def test_optimizer__interfaces__only_fragment_fields__from_one_fragment(graphql) -> None:
    graphql.schema = interface_schema()

    project_1 = ProjectFactory.create(name="Project 1")
    project_2 = ProjectFactory.create(name="Project 2")
    task_1 = TaskFactory.create(name="Task 1", type=TaskTypeChoices.TASK)
    task_2 = TaskFactory.create(name="Task 2", type=TaskTypeChoices.STORY)

    query = """
        query {
          named {
            ... on TaskType {
              type
            }
          }
        }
    """

    response = graphql(query, count_queries=True)

    assert response.has_errors is False, response.errors

    assert response.data == {"named": [{}, {}, {"type": "TASK"}, {"type": "STORY"}]}

    response.assert_query_count(2)


@pytest.mark.django_db
@pytest.mark.xfail(
    reason="Selecting a field (also `__typename`) directly on a `graphene.Interface` crashes the optimizer (unhandled graphene type).",
    strict=True,
)
def test_optimizer__interfaces__only_fragment_fields__from_one_fragment__typename(graphql) -> None:
    graphql.schema = interface_schema()

    project_1 = ProjectFactory.create(name="Project 1")
    project_2 = ProjectFactory.create(name="Project 2")
    task_1 = TaskFactory.create(name="Task 1", type=TaskTypeChoices.TASK)
    task_2 = TaskFactory.create(name="Task 2", type=TaskTypeChoices.STORY)

    query = """
        query {
          named {
            __typename
            ... on TaskType {
              type
            }
          }
        }
    """

    response = graphql(query, count_queries=True)

    assert response.has_errors is False, response.errors

    assert response.data == {
        "named": [
            {"__typename": "ProjectType"},
            {"__typename": "ProjectType"},
            {"__typename": "TaskType", "type": "TASK"},
            {"__typename": "TaskType", "type": "STORY"},
        ]
    }

    response.assert_query_count(2)


@pytest.mark.django_db
@pytest.mark.xfail(
    reason="Selecting a field (also `__typename`) directly on a `graphene.Interface` crashes the optimizer (unhandled graphene type).",
    strict=True,
)
def test_optimizer__interfaces__multiple_interface_fields(graphql) -> None:
    graphql.schema = interface_schema(with_id=True)

    project_1 = ProjectFactory.create(name="Project 1")
    project_2 = ProjectFactory.create(name="Project 2")
    task_1 = TaskFactory.create(name="Task 1", type=TaskTypeChoices.TASK)
    task_2 = TaskFactory.create(name="Task 2", type=TaskTypeChoices.STORY)

    query = """
        query {
          named {
            id
            name
            ... on ProjectType {
              pk
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
        "named": [
            {"id": project_1.pk, "pk": project_1.pk, "name": "Project 1"},
            {"id": project_2.pk, "pk": project_2.pk, "name": "Project 2"},
            {"id": task_1.pk, "name": "Task 1", "type": "TASK"},
            {"id": task_2.pk, "name": "Task 2", "type": "STORY"},
        ]
    }

    response.assert_query_count(2)


@pytest.mark.django_db
@pytest.mark.xfail(
    reason="Selecting a field (also `__typename`) directly on a `graphene.Interface` crashes the optimizer (unhandled graphene type).",
    strict=True,
)
def test_optimizer__interfaces__typename(graphql) -> None:
    graphql.schema = interface_schema()

    project_1 = ProjectFactory.create(name="Project 1")
    project_2 = ProjectFactory.create(name="Project 2")
    task_1 = TaskFactory.create(name="Task 1", type=TaskTypeChoices.TASK)
    task_2 = TaskFactory.create(name="Task 2", type=TaskTypeChoices.STORY)

    query = """
        query {
          named {
            __typename
            name
            ... on ProjectType {
              pk
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
        "named": [
            {"__typename": "ProjectType", "name": "Project 1", "pk": project_1.pk},
            {"__typename": "ProjectType", "name": "Project 2", "pk": project_2.pk},
            {"__typename": "TaskType", "name": "Task 1", "type": "TASK"},
            {"__typename": "TaskType", "name": "Task 2", "type": "STORY"},
        ]
    }

    response.assert_query_count(2)


@pytest.mark.skip(reason="No equivalent feature: filtering interface implementations with interface field arguments.")
def test_optimizer__interfaces__filtering() -> None: ...


@pytest.mark.skip(reason="No equivalent feature: ordering interface implementations with interface field arguments.")
def test_optimizer__interfaces__ordering() -> None: ...


@pytest.mark.django_db
@pytest.mark.xfail(
    reason="Selecting a field (also `__typename`) directly on a `graphene.Interface` crashes the optimizer (unhandled graphene type).",
    strict=True,
)
def test_optimizer__interfaces__skip_inline_fragment(graphql) -> None:
    graphql.schema = interface_schema()

    ProjectFactory.create(name="Project 1")
    TaskFactory.create(name="Task 1", type=TaskTypeChoices.TASK)

    query = """
        query {
          named {
            name
            ... on ProjectType @skip(if: true) {
              pk
            }
            ... on TaskType {
              type
            }
          }
        }
    """

    response = graphql(query, count_queries=True)

    assert response.has_errors is False, response.errors

    # ProjectType fragment was skipped, so only TaskType fields appear
    assert all("pk" not in item for item in response.data["named"])


@pytest.mark.django_db
@pytest.mark.xfail(
    reason="Inline fragment without a type condition crashes the optimizer (`type_condition` is `None`).",
    strict=True,
)
def test_optimizer__interfaces__inline_fragment_no_type_condition(graphql) -> None:
    graphql.schema = interface_schema()

    ProjectFactory.create(name="P1")
    TaskFactory.create(name="T1", type=TaskTypeChoices.BUG_FIX)

    query = """
        query {
          named {
            ... {
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

    assert response.data == {"named": [{"name": "P1"}, {"name": "T1", "type": "BUG_FIX"}]}

    response.assert_query_count(2)


@pytest.mark.django_db
@pytest.mark.xfail(
    reason="Selecting a field (also `__typename`) directly on a `graphene.Interface` crashes the optimizer (unhandled graphene type).",
    strict=True,
)
def test_optimizer__interfaces__inline_fragment_no_type_condition__holds_member_fragment(graphql) -> None:
    """A fragment without a type condition passes its member fragments on to the interface around it."""
    graphql.schema = interface_schema()

    ProjectFactory.create(name="P1")
    TaskFactory.create(name="T1", type=TaskTypeChoices.BUG_FIX)

    query = """
        query {
          named {
            name
            ... {
              ... on TaskType {
                type
              }
            }
          }
        }
    """

    response = graphql(query, count_queries=True)

    assert response.has_errors is False, response.errors

    assert response.data == {"named": [{"name": "P1"}, {"name": "T1", "type": "BUG_FIX"}]}

    response.assert_query_count(2)


@pytest.mark.django_db
@pytest.mark.xfail(
    reason="Selecting a field (also `__typename`) directly on a `graphene.Interface` crashes the optimizer (unhandled graphene type).",
    strict=True,
)
def test_optimizer__interfaces__no_other_fields(graphql) -> None:
    graphql.schema = interface_schema()

    ProjectFactory.create(name="Project 1")
    TaskFactory.create(name="Task 1", type=TaskTypeChoices.STORY)

    query = """
        query {
          named {
            name
          }
        }
    """

    response = graphql(query, count_queries=True)

    assert response.has_errors is False, response.errors

    assert len(response.data["named"]) == 2
