from __future__ import annotations

from typing import TYPE_CHECKING, Any

import graphene
import pytest
from django.db.models import Value

from example_project.undine_port.models import Comment, Person, Project, Task
from query_optimizer import DjangoListField, DjangoObjectType, ManuallyOptimizedField
from tests.undine_port.factories import CommentFactory, PersonFactory, ProjectFactory, TaskFactory

if TYPE_CHECKING:
    from django.db.models import Model, QuerySet

    from query_optimizer.optimizer import QueryOptimizer
    from query_optimizer.typing import GQLInfo


def task_schema() -> graphene.Schema:
    class ProjectType(DjangoObjectType):
        class Meta:
            model = Project
            fields = ["pk", "name"]

    class PersonType(DjangoObjectType):
        class Meta:
            model = Person
            fields = ["pk", "name"]

    class TaskType(DjangoObjectType):
        class Meta:
            model = Task
            fields = ["pk", "name", "project", "assignees"]

        assignees = DjangoListField(PersonType)

    class Query(graphene.ObjectType):
        tasks = DjangoListField(TaskType)
        projects = DjangoListField(ProjectType)

    return graphene.Schema(query=Query)


def comment_schema() -> graphene.Schema:
    class ProjectType(DjangoObjectType):
        class Meta:
            model = Project
            fields = ["pk", "name"]

    class TaskType(DjangoObjectType):
        class Meta:
            model = Task
            fields = ["pk", "name"]

    class CommentTarget(graphene.Union):
        class Meta:
            types = (ProjectType, TaskType)

        @classmethod
        def resolve_type(cls, instance: Model, info: GQLInfo) -> type[DjangoObjectType]:
            return ProjectType if isinstance(instance, Project) else TaskType

    class CommentType(DjangoObjectType):
        class Meta:
            model = Comment
            fields = ["pk"]

        target = graphene.Field(CommentTarget)

        def resolve_target(root: Comment, info: GQLInfo) -> Model | None:
            return root.target

    class Query(graphene.ObjectType):
        comments = DjangoListField(CommentType)

    return graphene.Schema(query=Query)


def calculation_schema() -> graphene.Schema:
    # Undine `Calculation` with a `CalculationArgument` -> `ManuallyOptimizedField` with `args`.
    class TaskType(DjangoObjectType):
        class Meta:
            model = Task
            fields = ["pk"]

        calc = ManuallyOptimizedField(graphene.Int, args={"value": graphene.Int(required=True)})

        @staticmethod
        def optimize_calc(queryset: QuerySet, optimizer: QueryOptimizer, **kwargs: Any) -> QuerySet:
            return queryset.annotate(calc=Value(kwargs["value"]))

        def resolve_calc(root: Task, info: GQLInfo, **kwargs: Any) -> int:
            return root.calc  # type: ignore[attr-defined]

    class Query(graphene.ObjectType):
        tasks = DjangoListField(TaskType)

    return graphene.Schema(query=Query)


@pytest.mark.django_db
def test_optimizer__aliases__entrypoint(graphql) -> None:
    graphql.schema = task_schema()

    task_1 = TaskFactory.create(name="foo")
    task_2 = TaskFactory.create(name="bar")

    query = """
        query {
         myTasks: tasks {
            pk
            name
          }
        }
    """

    response = graphql(query, count_queries=True)
    assert response.has_errors is False, response.errors

    assert response.data == {
        "myTasks": [
            {
                "pk": task_1.pk,
                "name": "foo",
            },
            {
                "pk": task_2.pk,
                "name": "bar",
            },
        ],
    }

    response.assert_query_count(1)


@pytest.mark.django_db
def test_optimizer__aliases__model_field(graphql) -> None:
    graphql.schema = task_schema()

    task_1 = TaskFactory.create(name="foo")
    task_2 = TaskFactory.create(name="bar")

    query = """
        query {
          tasks {
            pk
            title: name
          }
        }
    """

    response = graphql(query, count_queries=True)
    assert response.has_errors is False, response.errors

    assert response.data == {
        "tasks": [
            {
                "pk": task_1.pk,
                "title": "foo",
            },
            {
                "pk": task_2.pk,
                "title": "bar",
            },
        ],
    }

    response.assert_query_count(1)


@pytest.mark.django_db
def test_optimizer__aliases__model_field__multiple(graphql) -> None:
    graphql.schema = task_schema()

    task_1 = TaskFactory.create(name="foo")
    task_2 = TaskFactory.create(name="bar")

    query = """
        query {
          tasks {
            pk
            foo: name
            bar: name
          }
        }
    """

    response = graphql(query, count_queries=True)
    assert response.has_errors is False, response.errors

    assert response.data == {
        "tasks": [
            {
                "pk": task_1.pk,
                "foo": "foo",
                "bar": "foo",
            },
            {
                "pk": task_2.pk,
                "foo": "bar",
                "bar": "bar",
            },
        ],
    }

    response.assert_query_count(1)


@pytest.mark.django_db
def test_optimizer__aliases__related_field__to_one(graphql) -> None:
    graphql.schema = task_schema()

    project_1 = ProjectFactory.create(name="foo")
    project_2 = ProjectFactory.create(name="bar")

    task_1 = TaskFactory.create(name="foo", project=project_1)
    task_2 = TaskFactory.create(name="bar", project=project_2)

    query = """
        query {
          tasks {
            pk
            name
            in: project {
              pk
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
                "pk": task_1.pk,
                "name": "foo",
                "in": {
                    "pk": project_1.pk,
                    "name": "foo",
                },
            },
            {
                "pk": task_2.pk,
                "name": "bar",
                "in": {
                    "pk": project_2.pk,
                    "name": "bar",
                },
            },
        ],
    }

    response.assert_query_count(1)


@pytest.mark.django_db
def test_optimizer__aliases__related_field__to_one__multiple(graphql) -> None:
    graphql.schema = task_schema()

    project_1 = ProjectFactory.create(name="foo")
    project_2 = ProjectFactory.create(name="bar")

    task_1 = TaskFactory.create(name="foo", project=project_1)
    task_2 = TaskFactory.create(name="bar", project=project_2)

    query = """
        query {
          tasks {
            pk
            name
            foo: project {
              pk
            }
            bar: project {
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
                "pk": task_1.pk,
                "name": "foo",
                "foo": {
                    "pk": project_1.pk,
                },
                "bar": {
                    "name": "foo",
                },
            },
            {
                "pk": task_2.pk,
                "name": "bar",
                "foo": {
                    "pk": project_2.pk,
                },
                "bar": {
                    "name": "bar",
                },
            },
        ],
    }

    # Don't make separate prefetches for the aliased to-one relations.
    response.assert_query_count(1)


@pytest.mark.django_db
def test_optimizer__aliases__related_field__to_many(graphql) -> None:
    graphql.schema = task_schema()

    task_1 = TaskFactory.create(name="foo")
    task_2 = TaskFactory.create(name="bar")

    person_1 = PersonFactory.create(name="foo", tasks=[task_1])
    person_2 = PersonFactory.create(name="bar", tasks=[task_1])
    person_3 = PersonFactory.create(name="baz", tasks=[task_2])
    person_4 = PersonFactory.create(name="bax", tasks=[task_2])

    query = """
        query {
          tasks {
            pk
            name
            by: assignees {
              pk
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
                "pk": task_1.pk,
                "name": "foo",
                "by": [
                    {"pk": person_1.pk, "name": "foo"},
                    {"pk": person_2.pk, "name": "bar"},
                ],
            },
            {
                "pk": task_2.pk,
                "name": "bar",
                "by": [
                    {"pk": person_3.pk, "name": "baz"},
                    {"pk": person_4.pk, "name": "bax"},
                ],
            },
        ],
    }

    response.assert_query_count(2)


@pytest.mark.django_db
def test_optimizer__aliases__related_field__to_many__multiple(graphql) -> None:
    graphql.schema = task_schema()

    task_1 = TaskFactory.create(name="foo")
    task_2 = TaskFactory.create(name="bar")

    person_1 = PersonFactory.create(name="foo", tasks=[task_1])
    person_2 = PersonFactory.create(name="bar", tasks=[task_1])
    person_3 = PersonFactory.create(name="baz", tasks=[task_2])
    person_4 = PersonFactory.create(name="bax", tasks=[task_2])

    query = """
        query {
          tasks {
            pk
            name
            foo: assignees {
              pk
            }
            bar: assignees {
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
                "pk": task_1.pk,
                "name": "foo",
                "foo": [
                    {"pk": person_1.pk},
                    {"pk": person_2.pk},
                ],
                "bar": [
                    {"name": "foo"},
                    {"name": "bar"},
                ],
            },
            {
                "pk": task_2.pk,
                "name": "bar",
                "foo": [
                    {"pk": person_3.pk},
                    {"pk": person_4.pk},
                ],
                "bar": [
                    {"name": "baz"},
                    {"name": "bax"},
                ],
            },
        ],
    }

    # Need to make separate prefetches for the aliased to-many relations,
    # since they might have different filtering/ordering applied.
    response.assert_query_count(3)


@pytest.mark.django_db
def test_optimizer__aliases__related_field__generic_foreign_key(graphql) -> None:
    graphql.schema = comment_schema()

    task = TaskFactory.create(name="Task")
    project = ProjectFactory.create(name="Project")
    CommentFactory.create(contents="foo", target=task)
    CommentFactory.create(contents="bar", target=project)

    query = """
        query {
          comments {
            to: target {
              ... on ProjectType {
                name
              }
              ... on TaskType {
                name
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
                "to": {"name": "Task"},
            },
            {
                "to": {"name": "Project"},
            },
        ],
    }

    response.assert_query_count(3)


@pytest.mark.django_db
def test_optimizer__aliases__related_field__generic_foreign_key__multiple(graphql) -> None:
    graphql.schema = comment_schema()

    task = TaskFactory.create(name="Task")
    project = ProjectFactory.create(name="Project")
    CommentFactory.create(contents="foo", target=task)
    CommentFactory.create(contents="bar", target=project)

    query = """
        query {
          comments {
            foo: target {
              ... on ProjectType {
                pk
              }
              ... on TaskType {
                pk
              }
            }
            bar: target {
              ... on ProjectType {
                name
              }
              ... on TaskType {
                name
              }
            }
          }
        }
    """

    response = graphql(query, count_queries=True)
    assert response.has_errors is False, response.errors

    # Undine asserts `pk == 1`, which depends on the database resetting primary key sequences.
    assert response.data == {
        "comments": [
            {
                "foo": {"pk": task.pk},
                "bar": {"name": "Task"},
            },
            {
                "foo": {"pk": project.pk},
                "bar": {"name": "Project"},
            },
        ]
    }

    response.assert_query_count(3)


@pytest.mark.django_db
@pytest.mark.xfail(
    reason=(
        "Arguments of an aliased `ManuallyOptimizedField` are lost: manual optimizers are stored "
        "by field name, but filter info is stored by alias."
    ),
    strict=True,
)
def test_optimizer__aliases__calculated(graphql) -> None:
    graphql.schema = calculation_schema()

    task_1 = TaskFactory.create(name="foo")
    task_2 = TaskFactory.create(name="bar")

    query = """
        query {
          tasks {
            pk
            calculation: calc(value: 1)
          }
        }
    """

    response = graphql(query, count_queries=True)
    assert response.has_errors is False, response.errors

    assert response.data == {
        "tasks": [
            {
                "pk": task_1.pk,
                "calculation": 1,
            },
            {
                "pk": task_2.pk,
                "calculation": 1,
            },
        ],
    }

    response.assert_query_count(1)


@pytest.mark.django_db
@pytest.mark.xfail(
    reason=(
        "Arguments of an aliased `ManuallyOptimizedField` are lost. Furthermore, a field can only "
        "have one manual optimizer, so aliases with different arguments cannot get different values."
    ),
    strict=True,
)
def test_optimizer__aliases__calculated__multiple(graphql) -> None:
    graphql.schema = calculation_schema()

    task_1 = TaskFactory.create(name="foo")
    task_2 = TaskFactory.create(name="bar")

    query = """
        query {
          tasks {
            pk
            foo: calc(value: 1)
            bar: calc(value: 2)
          }
        }
    """

    response = graphql(query, count_queries=True)
    assert response.has_errors is False, response.errors

    assert response.data == {
        "tasks": [
            {
                "pk": task_1.pk,
                "foo": 1,
                "bar": 2,
            },
            {
                "pk": task_2.pk,
                "foo": 1,
                "bar": 2,
            },
        ],
    }

    response.assert_query_count(1)
