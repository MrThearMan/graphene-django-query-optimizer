from __future__ import annotations

from typing import TYPE_CHECKING, Any

import graphene
import pytest
from django.db.models import Value
from django.db.models.functions import Left
from django_filters import FilterSet

from example_project.undine_port.models import Project, Task
from query_optimizer import AnnotatedField, DjangoListField, DjangoObjectType, ManuallyOptimizedField
from tests.undine_port.factories import TaskFactory

if TYPE_CHECKING:
    from django.db.models import QuerySet

    from query_optimizer.optimizer import QueryOptimizer
    from query_optimizer.typing import GQLInfo


def schema_for(project_type: type[DjangoObjectType]) -> graphene.Schema:
    class TaskType(DjangoObjectType):
        class Meta:
            model = Task
            fields = ["name", "project"]

        project = graphene.Field(project_type)

    class Query(graphene.ObjectType):
        tasks = DjangoListField(TaskType)

    return graphene.Schema(query=Query)


@pytest.mark.django_db
@pytest.mark.xfail(
    reason=(
        "`filter_queryset` of a to-one related type is ignored, since the relation is "
        "fetched with `select_related`. It is only promoted to a prefetch for annotations."
    ),
    strict=True,
)
def test_optimizer__promote_to_prefetch__has_filter_queryset(graphql) -> None:
    class ProjectType(DjangoObjectType):
        class Meta:
            model = Project
            fields = ["name"]

        @classmethod
        def filter_queryset(cls, queryset: QuerySet, info: GQLInfo) -> QuerySet:
            return queryset.filter(name="foo")

    graphql.schema = schema_for(ProjectType)

    TaskFactory.create(name="task 1", project__name="foo")
    TaskFactory.create(name="task 2", project__name="bar")

    query = """
        query {
          tasks {
            name
            project {
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
                "name": "task 1",
                "project": {"name": "foo"},
            },
            {
                "name": "task 2",
                "project": None,
            },
        ],
    }

    # Normally, project would be fetched in a single
    # query with the task since its a to-one relation,
    # but since the object type has a 'filter_queryset' method,
    # we need to use 'prefetch_related' instead or 'select_related'.
    assert len(response.queries) == 2


@pytest.mark.django_db
def test_optimizer__promote_to_prefetch__has_annotations(graphql) -> None:
    class ProjectType(DjangoObjectType):
        class Meta:
            model = Project
            fields = ["name"]

        first_letter = AnnotatedField(graphene.String, Left("name", 1))

    graphql.schema = schema_for(ProjectType)

    TaskFactory.create(name="task 1", project__name="foo")
    TaskFactory.create(name="task 2", project__name="bar")

    query = """
        query {
          tasks {
            name
            project {
              firstLetter
            }
          }
        }
    """

    response = graphql(query, count_queries=True)
    assert response.has_errors is False, response.errors

    assert response.data == {
        "tasks": [
            {
                "name": "task 1",
                "project": {"firstLetter": "f"},
            },
            {
                "name": "task 2",
                "project": {"firstLetter": "b"},
            },
        ],
    }

    # Normally, project would be fetched in a single
    # query with the task since its a to-one relation,
    # but since the there is an annotation on project,
    # we need to use 'prefetch_related' instead or 'select_related'.
    assert len(response.queries) == 2


@pytest.mark.django_db
@pytest.mark.xfail(
    reason=(
        "Manual optimizers of a to-one related type run on a queryset that is discarded, "
        "since the relation is only promoted to a prefetch for annotations."
    ),
    strict=True,
)
def test_optimizer__promote_to_prefetch__has_field_calculations(graphql) -> None:
    # Undine `Calculation` with a `CalculationArgument` -> `ManuallyOptimizedField` with `args`.
    class ProjectType(DjangoObjectType):
        class Meta:
            model = Project
            fields = ["name"]

        custom = ManuallyOptimizedField(graphene.Int, args={"value": graphene.Int(required=True)})

        @staticmethod
        def optimize_custom(queryset: QuerySet, optimizer: QueryOptimizer, **kwargs: Any) -> QuerySet:
            return queryset.annotate(custom=Value(kwargs["value"]))

        def resolve_custom(root: Project, info: GQLInfo, **kwargs: Any) -> int:
            return root.custom  # type: ignore[attr-defined]

    graphql.schema = schema_for(ProjectType)

    TaskFactory.create(name="task 1", project__name="foo")
    TaskFactory.create(name="task 2", project__name="bar")

    query = """
        query {
          tasks {
            name
            project {
              custom(value: 1)
            }
          }
        }
    """

    response = graphql(query, count_queries=True)
    assert response.has_errors is False, response.errors

    assert response.data == {
        "tasks": [
            {
                "name": "task 1",
                "project": {"custom": 1},
            },
            {
                "name": "task 2",
                "project": {"custom": 1},
            },
        ],
    }

    # Normally, project would be fetched in a single
    # query with the task since its a to-one relation,
    # but since there is a field calculation on project,
    # we need to use 'prefetch_related' instead of 'select_related'.
    assert len(response.queries) == 2


@pytest.mark.django_db
@pytest.mark.xfail(
    reason=(
        "FilterSet filtering of a to-one related type is ignored, since the relation is "
        "fetched with `select_related`. It is only promoted to a prefetch for annotations."
    ),
    strict=True,
)
def test_optimizer__promote_to_prefetch__has_filterset_filter_queryset(graphql) -> None:
    # Undine `FilterSet.__filter_queryset__` -> django-filter `FilterSet.filter_queryset`.
    class ProjectFilterSet(FilterSet):
        class Meta:
            model = Project
            fields = ["name"]

        def filter_queryset(self, queryset: QuerySet) -> QuerySet:
            return super().filter_queryset(queryset).filter(name="foo")

    class ProjectType(DjangoObjectType):
        class Meta:
            model = Project
            fields = ["name"]
            filterset_class = ProjectFilterSet

    graphql.schema = schema_for(ProjectType)

    TaskFactory.create(name="task 1", project__name="foo")
    TaskFactory.create(name="task 2", project__name="bar")

    query = """
        query {
          tasks {
            name
            project {
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
                "name": "task 1",
                "project": {"name": "foo"},
            },
            {
                "name": "task 2",
                "project": None,
            },
        ],
    }

    # Normally, project would be fetched in a single
    # query with the task since its a to-one relation,
    # but since the object type has a FilterSet with a 'filter_queryset' method,
    # we need to use 'prefetch_related' instead of 'select_related'.
    assert len(response.queries) == 2
