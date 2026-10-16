from __future__ import annotations

from typing import TYPE_CHECKING, Any

import graphene
import pytest
from django.core.exceptions import PermissionDenied

from example_project.undine_port.models import Comment, Person, Project, Task, TaskTypeChoices, Team
from query_optimizer import DjangoListField, DjangoObjectType, MultiField
from query_optimizer.optimizer import QueryOptimizer
from tests.undine_port.factories import CommentFactory, PersonFactory, ProjectFactory, TaskFactory, TeamFactory

if TYPE_CHECKING:
    from django.db.models import QuerySet

    from query_optimizer.typing import GQLInfo


# Undine `QueryType.__optimize__` -> `DjangoObjectType.pre_optimization_hook`.
# Undine `OptimizationData.add_select_related/add_prefetch_related` -> adding child `QueryOptimizer`s.


def add_child(
    optimizer: QueryOptimizer,
    name: str,
    model: type | None,
    *,
    set_as: str = "select_related",
) -> QueryOptimizer:
    child = QueryOptimizer(model=model, info=optimizer.info, name=name, parent=optimizer)
    return optimizer.get_or_set_child_optimizer(name, child, set_as=set_as)  # type: ignore[arg-type]


@pytest.mark.django_db
def test_optimizer__manual_optimization__query_type(graphql) -> None:
    # Undine checks permissions for each instance in `__permissions__` using the logged-in user.
    # This project has no per-instance permission hook for lists, so the check is done in the resolver,
    # with a fixed email instead of a logged-in user. This removes the query for fetching the user.
    user_email = "me@example.com"

    class TaskType(DjangoObjectType):
        class Meta:
            model = Task
            fields = ["name"]

        @classmethod
        def pre_optimization_hook(cls, queryset: QuerySet, optimizer: QueryOptimizer) -> QuerySet:
            optimizer.related_fields.append("project_id")
            project_optimizer = add_child(optimizer, "project", Project)
            project_optimizer.related_fields.append("team_id")
            team_optimizer = add_child(project_optimizer, "team", Team)
            member_optimizer = add_child(team_optimizer, "members", Person, set_as="prefetch_related")
            member_optimizer.only_fields.append("email")
            return queryset

        def resolve_name(root: Task, info: GQLInfo) -> str:
            if not root.project:
                raise PermissionDenied

            if not root.project.team:
                raise PermissionDenied

            member_emails = {member.email for member in root.project.team.members.all()}
            if user_email not in member_emails:
                raise PermissionDenied

            return root.name

    class Query(graphene.ObjectType):
        tasks = DjangoListField(TaskType)

    graphql.schema = graphene.Schema(query=Query)

    person_1 = PersonFactory.create(name="person 1", email="me@example.com")
    person_2 = PersonFactory.create(name="person 2", email="you@example.com")

    team_1 = TeamFactory.create(name="team 1", members=[person_1])
    team_2 = TeamFactory.create(name="team 2", members=[person_1, person_2])

    project_1 = ProjectFactory.create(name="project", team=team_1)
    project_2 = ProjectFactory.create(name="project", team=team_2)

    TaskFactory.create(name="task 1", project=project_1)
    TaskFactory.create(name="task 2", project=project_1)
    TaskFactory.create(name="task 3", project=project_2)

    query = """
        query {
          tasks {
            name
          }
        }
    """

    response = graphql(query, count_queries=True)
    assert response.has_errors is False, response.errors

    assert response.data == {
        "tasks": [
            {"name": "task 1"},
            {"name": "task 2"},
            {"name": "task 3"},
        ],
    }

    # Queries
    # 1. Fetch tasks with projects and teams
    # 2. Fetch members of teams
    response.assert_query_count(2)


@pytest.mark.django_db
def test_optimizer__manual_optimization__field(graphql) -> None:
    # Undine field-level `@<field>.optimize` -> `MultiField` with the needed model fields.
    class TaskStatus(graphene.ObjectType):
        name = graphene.String()
        type = graphene.String()

    class TaskType(DjangoObjectType):
        class Meta:
            model = Task
            fields = ["pk"]

        status = MultiField(TaskStatus, fields=["name", "type"])

        def resolve_status(root: Task, info: GQLInfo) -> dict[str, Any]:
            return {"name": root.name, "type": TaskTypeChoices(root.type).value}

    class Query(graphene.ObjectType):
        tasks = DjangoListField(TaskType)

    graphql.schema = graphene.Schema(query=Query)

    task_1 = TaskFactory.create(name="task 1", type=TaskTypeChoices.STORY)
    task_2 = TaskFactory.create(name="task 2", type=TaskTypeChoices.TASK)

    query = """
        query {
          tasks {
            pk
            status {
              name
              type
            }
          }
        }
    """

    response = graphql(query, count_queries=True)
    assert response.has_errors is False, response.errors

    assert response.data == {
        "tasks": [
            {
                "pk": task_1.pk,
                "status": {
                    "name": "task 1",
                    "type": "STORY",
                },
            },
            {
                "pk": task_2.pk,
                "status": {
                    "name": "task 2",
                    "type": "TASK",
                },
            },
        ],
    }

    # Queries
    # 1. Fetch tasks with correct fields
    response.assert_query_count(1)


@pytest.mark.django_db
def test_optimizer__manual_optimization__add_select_related(graphql) -> None:
    class ProjectType(DjangoObjectType):
        class Meta:
            model = Project
            fields = ["name"]

    class TaskType(DjangoObjectType):
        class Meta:
            model = Task
            fields = ["name"]

        @classmethod
        def pre_optimization_hook(cls, queryset: QuerySet, optimizer: QueryOptimizer) -> QuerySet:
            optimizer.related_fields.append("project_id")
            add_child(optimizer, "project", Project)
            return queryset

    class Query(graphene.ObjectType):
        tasks = DjangoListField(TaskType)
        projects = DjangoListField(ProjectType)

    graphql.schema = graphene.Schema(query=Query)

    ProjectFactory.create(name="Proj")
    TaskFactory.create(name="T1", project=Project.objects.first())

    query = "query { tasks { name } }"
    response = graphql(query, count_queries=True)
    assert response.has_errors is False, response.errors

    response.assert_query_count(1)


@pytest.mark.skip(reason="No equivalent feature: Undine's deprecated `__optimizations__` name.")
def test_optimizer__manual_optimization__deprecated_name() -> None: ...


@pytest.mark.django_db
def test_optimizer__manual_optimization__add_prefetch_related(graphql) -> None:
    class PersonType(DjangoObjectType):
        class Meta:
            model = Person
            fields = ["name"]

    class TaskType(DjangoObjectType):
        class Meta:
            model = Task
            fields = ["name"]

        @classmethod
        def pre_optimization_hook(cls, queryset: QuerySet, optimizer: QueryOptimizer) -> QuerySet:
            add_child(optimizer, "assignees", Person, set_as="prefetch_related")
            return queryset

    class Query(graphene.ObjectType):
        tasks = DjangoListField(TaskType)
        people = DjangoListField(PersonType)

    graphql.schema = graphene.Schema(query=Query)

    person = PersonFactory.create(name="Bob")
    TaskFactory.create(name="T1", assignees=[person])

    query = "query { tasks { name } }"
    response = graphql(query, count_queries=True)
    assert response.has_errors is False, response.errors

    response.assert_query_count(2)


@pytest.mark.django_db
def test_optimizer__manual_optimization__add_generic_prefetch_related(graphql) -> None:
    class TaskType(DjangoObjectType):
        class Meta:
            model = Task
            fields = ["type"]

    class CommentTarget(graphene.Union):
        class Meta:
            types = (TaskType,)

        @classmethod
        def resolve_type(cls, instance: Any, info: GQLInfo) -> type[DjangoObjectType]:
            return TaskType

    class CommentType(DjangoObjectType):
        class Meta:
            model = Comment
            fields = ["pk"]

        target = graphene.Field(CommentTarget)

        def resolve_target(root: Comment, info: GQLInfo) -> Any:
            return root.target

        @classmethod
        def pre_optimization_hook(cls, queryset: QuerySet, optimizer: QueryOptimizer) -> QuerySet:
            optimizer.related_fields.extend(["content_type", "object_id"])
            add_child(optimizer, "target", None, set_as="prefetch_related")
            return queryset

    class Query(graphene.ObjectType):
        comments = DjangoListField(CommentType)

    graphql.schema = graphene.Schema(query=Query)

    task = TaskFactory.create(type=TaskTypeChoices.STORY.value)
    CommentFactory.create(contents="c", target=task)

    query = "query { comments { target { ... on TaskType { type } } } }"
    response = graphql(query, count_queries=True)

    assert response.has_errors is False, response.errors

    response.assert_query_count(2)
