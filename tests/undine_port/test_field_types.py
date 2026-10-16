from __future__ import annotations

from typing import TYPE_CHECKING, Any

import graphene
import pytest
from django.db.models import Case, IntegerField, Value, When
from django.db.models.functions import Left

from example_project.undine_port.models import Task
from query_optimizer import AnnotatedField, DjangoListField, DjangoObjectType, ManuallyOptimizedField
from tests.undine_port.factories import TaskFactory

if TYPE_CHECKING:
    from django.db.models import QuerySet

    from query_optimizer.optimizer import QueryOptimizer


def schema_for(task_type: type[DjangoObjectType]) -> graphene.Schema:
    class Query(graphene.ObjectType):
        tasks = DjangoListField(task_type)

    return graphene.Schema(query=Query)


@pytest.mark.django_db
def test_optimizer__fields__expression(graphql) -> None:
    class TaskType(DjangoObjectType):
        class Meta:
            model = Task
            fields = ["pk"]

        first_letter = AnnotatedField(graphene.String, Left("name", 1))

    graphql.schema = schema_for(TaskType)

    TaskFactory.create(name="foo")

    query = """
        query {
          tasks {
            firstLetter
          }
        }
    """

    response = graphql(query)
    assert response.has_errors is False, response.errors

    assert response.data == {"tasks": [{"firstLetter": "f"}]}


@pytest.mark.django_db
def test_optimizer__fields__schema_name(graphql) -> None:
    class TaskType(DjangoObjectType):
        class Meta:
            model = Task
            fields = ["name"]

    graphql.schema = schema_for(TaskType)

    TaskFactory.create(name="foo")

    query = """
        query {
          tasks {
            __typename
          }
        }
    """

    response = graphql(query)
    assert response.has_errors is False, response.errors

    assert response.data == {"tasks": [{"__typename": "TaskType"}]}


@pytest.mark.django_db
def test_optimizer__fields__calculated_field(graphql) -> None:
    # Undine `Calculation` with a `CalculationArgument` -> `ManuallyOptimizedField` with `args`.
    class TaskType(DjangoObjectType):
        class Meta:
            model = Task
            fields = ["name"]

        calculated_number = ManuallyOptimizedField(graphene.Int, args={"value": graphene.Int(required=True)})

        @staticmethod
        def optimize_calculated_number(queryset: QuerySet, optimizer: QueryOptimizer, **kwargs: Any) -> QuerySet:
            return queryset.annotate(
                calculated_number=Case(
                    When(name="foo", then=Value(None)),
                    default=Value(kwargs["value"]),
                    output_field=IntegerField(null=True),
                ),
            )

        def resolve_calculated_number(root: Task, info: Any, **kwargs: Any) -> int | None:
            return root.calculated_number  # type: ignore[attr-defined]

    graphql.schema = schema_for(TaskType)

    TaskFactory.create(name="foo")
    TaskFactory.create(name="bar")
    TaskFactory.create(name="baz")

    query = """
        query {
          tasks {
            name
            calculatedNumber(value: 1)
          }
        }
    """

    response = graphql(query)
    assert response.has_errors is False, response.errors

    assert response.data == {
        "tasks": [
            {
                "name": "foo",
                "calculatedNumber": None,
            },
            {
                "name": "bar",
                "calculatedNumber": 1,
            },
            {
                "name": "baz",
                "calculatedNumber": 1,
            },
        ],
    }


@pytest.mark.django_db
def test_optimizer__fields__to_one_field(graphql) -> None:
    # Undine renders a related field without a QueryType as the primary key of the related object.
    class TaskType(DjangoObjectType):
        class Meta:
            model = Task
            fields = ["pk"]

        project = graphene.Int()

        def resolve_project(root: Task, info: Any) -> int | None:
            return root.project.pk if root.project is not None else None

    graphql.schema = schema_for(TaskType)

    task = TaskFactory.create(name="foo", project__name="bar")
    project = task.project

    query = """
        query {
          tasks {
            project
          }
        }
    """

    response = graphql(query)
    assert response.has_errors is False, response.errors

    assert response.data == {"tasks": [{"project": project.pk}]}


@pytest.mark.django_db
def test_optimizer__fields__to_many_field(graphql) -> None:
    # Undine renders a related field without a QueryType as the primary keys of the related objects.
    class TaskType(DjangoObjectType):
        class Meta:
            model = Task
            fields = ["pk"]

        assignees = graphene.List(graphene.Int)

        def resolve_assignees(root: Task, info: Any) -> list[int]:
            return [assignee.pk for assignee in root.assignees.all()]

    graphql.schema = schema_for(TaskType)

    task = TaskFactory.create(name="foo", assignees__name="bar")
    assignee = task.assignees.first()

    query = """
        query {
          tasks {
            assignees
          }
        }
    """

    response = graphql(query)
    assert response.has_errors is False, response.errors

    assert response.data == {"tasks": [{"assignees": [assignee.pk]}]}
