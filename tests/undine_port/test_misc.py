from __future__ import annotations

from typing import TYPE_CHECKING

import graphene
import pytest
from django_filters import BooleanFilter, CharFilter, FilterSet

from example_project.undine_port.models import Person, Project, Task, Team
from query_optimizer import DjangoListField, DjangoObjectType
from tests.undine_port.factories import PersonFactory, ProjectFactory, TaskFactory, TeamFactory

if TYPE_CHECKING:
    from django.db.models import QuerySet


@pytest.mark.django_db
def test_optimizer__multiple_queries(graphql) -> None:
    class ProjectType(DjangoObjectType):
        class Meta:
            model = Project
            fields = ["name"]

    class TaskType(DjangoObjectType):
        class Meta:
            model = Task
            fields = ["name"]

    class Query(graphene.ObjectType):
        tasks = DjangoListField(TaskType)
        projects = DjangoListField(ProjectType)

    graphql.schema = graphene.Schema(query=Query)

    project = ProjectFactory.create(name="foo")
    TaskFactory.create(name="foo", project=project)

    query = """
        query {
          tasks {
            name
          }
          projects {
            name
          }
        }
    """

    response = graphql(query, count_queries=True)
    assert response.has_errors is False, response.errors

    assert response.data == {"tasks": [{"name": "foo"}], "projects": [{"name": "foo"}]}


@pytest.mark.skip(reason="No equivalent feature: `optimize` has no `limit` argument.")
def test_optimizer__optimize_sync__with_limit() -> None: ...


@pytest.mark.skip(reason="No equivalent feature: no async optimizer.")
def test_optimizer__optimize_async__with_kwargs() -> None: ...


@pytest.mark.skip(reason="No equivalent feature: no async optimizer.")
def test_optimizer__optimize_async__with_limit() -> None: ...


@pytest.mark.django_db
def test_optimizer__handle_undine_field__no_undine_field(graphql) -> None:
    class TaskType(DjangoObjectType):
        class Meta:
            model = Task
            fields = ["name", "done"]

    class Query(graphene.ObjectType):
        tasks = DjangoListField(TaskType)

    graphql.schema = graphene.Schema(query=Query)

    TaskFactory.create(name="foo", done=True)

    response = graphql("query { tasks { name done } }")
    assert response.has_errors is False, response.errors
    assert response.data == {"tasks": [{"name": "foo", "done": True}]}


@pytest.mark.django_db
def test_optimizer__extend__prefetch_in_select_related(graphql) -> None:
    class PersonType(DjangoObjectType):
        class Meta:
            model = Person
            fields = ["name"]

    class TeamType(DjangoObjectType):
        class Meta:
            model = Team
            fields = ["name", "members"]

        members = DjangoListField(PersonType)

    class ProjectType(DjangoObjectType):
        class Meta:
            model = Project
            fields = ["name", "team"]

    class TaskType2(DjangoObjectType):
        class Meta:
            model = Task
            fields = ["name", "project"]

    class Query(graphene.ObjectType):
        tasks = DjangoListField(TaskType2)

    graphql.schema = graphene.Schema(query=Query)

    person = PersonFactory.create(name="Alice")
    team = TeamFactory.create(name="T1", members=[person])
    project = ProjectFactory.create(name="P1", team=team)
    TaskFactory.create(name="Task1", project=project)

    query = """
        query {
          tasks {
            name
            project {
              name
              team {
                name
                members {
                  name
                }
              }
            }
          }
        }
    """

    response = graphql(query, count_queries=True)
    assert response.has_errors is False, response.errors
    assert response.data["tasks"][0]["project"]["team"]["members"] == [{"name": "Alice"}]


@pytest.mark.django_db
def test_optimizer__apply__select_related_and_only(graphql) -> None:
    class ProjectType(DjangoObjectType):
        class Meta:
            model = Project
            fields = ["name"]

    class TaskType(DjangoObjectType):
        class Meta:
            model = Task
            fields = ["name", "project"]

    class Query(graphene.ObjectType):
        tasks = DjangoListField(TaskType)

    graphql.schema = graphene.Schema(query=Query)

    project = ProjectFactory.create(name="P")
    TaskFactory.create(name="T", project=project)

    response = graphql("query { tasks { name project { name } } }", count_queries=True)
    assert response.has_errors is False, response.errors
    response.assert_query_count(1)


@pytest.mark.django_db
def test_optimizer__apply__none_queryset(graphql) -> None:
    # Undine `EmptyFilterResult` -> django-filter method filter that returns `queryset.none()`.
    class TaskFilterSet(FilterSet):
        none_filter = BooleanFilter(method="filter_none")

        class Meta:
            model = Task
            fields: list[str] = []

        def filter_none(self, queryset: QuerySet, name: str, value: bool) -> QuerySet:  # noqa: FBT001
            return queryset.none()

    class TaskType(DjangoObjectType):
        class Meta:
            model = Task
            fields = ["name"]
            filterset_class = TaskFilterSet

    class Query(graphene.ObjectType):
        tasks = DjangoListField(TaskType)

    graphql.schema = graphene.Schema(query=Query)

    TaskFactory.create(name="should-not-appear")

    query = """
        query {
          tasks(noneFilter: true) {
            name
          }
        }
    """

    response = graphql(query)
    assert response.has_errors is False, response.errors
    assert response.data == {"tasks": []}


@pytest.mark.skip(reason="No equivalent feature: aliases for orderings.")
def test_optimizer__apply__with_aliases() -> None: ...


@pytest.mark.django_db
def test_optimizer__apply__with_distinct(graphql) -> None:
    class TaskFilterSet(FilterSet):
        name = CharFilter(distinct=True)

        class Meta:
            model = Task
            fields: list[str] = []

    class TaskType(DjangoObjectType):
        class Meta:
            model = Task
            fields = ["name"]
            filterset_class = TaskFilterSet

    class Query(graphene.ObjectType):
        tasks = DjangoListField(TaskType)

    graphql.schema = graphene.Schema(query=Query)

    TaskFactory.create(name="T1")
    TaskFactory.create(name="T2")

    query = """
        query {
          tasks(name: "T1") {
            name
          }
        }
    """

    response = graphql(query)
    assert response.has_errors is False, response.errors
    assert response.data == {"tasks": [{"name": "T1"}]}


@pytest.mark.django_db
def test_optimizer__max_query_complexity(graphql) -> None:
    # Undine `MAX_QUERY_COMPLEXITY` -> `max_complexity` on the object type.
    # Undine counts the root field to the complexity (6), this project only counts the relations (5).
    # Therefore, the limit is one lower than in Undine.
    class ProjectType(DjangoObjectType):
        class Meta:
            model = Project
            fields = ["name", "tasks"]

    class TaskType(DjangoObjectType):
        class Meta:
            model = Task
            fields = ["name", "project"]
            max_complexity = 4

    class Query(graphene.ObjectType):
        tasks = DjangoListField(TaskType)

    graphql.schema = graphene.Schema(query=Query)

    project = ProjectFactory.create(name="foo")
    TaskFactory.create(name="bar", project=project)
    TaskFactory.create(name="baz", project=project)
    TaskFactory.create(name="buzz", project=project)

    query = """
        query {
          tasks {
            project {
              tasks {
                project {
                  tasks {
                    project {
                      name
                    }
                  }
                }
              }
            }
          }
        }
    """

    response = graphql(query)
    assert response.error_message(0) == "Query complexity exceeds the maximum allowed of 4"


@pytest.mark.skip(reason="No equivalent feature: maximum number of filters per type.")
def test_optimizer__too_many_filters() -> None: ...


@pytest.mark.skip(reason="No equivalent feature: maximum number of orderings per type.")
def test_optimizer__too_many_orders() -> None: ...
