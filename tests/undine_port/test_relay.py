from __future__ import annotations

import dataclasses
from typing import TYPE_CHECKING, Any

import graphene
import pytest
from graphene import relay
from graphql_relay import offset_to_cursor, to_global_id

from example_project.undine_port.models import Comment, Person, Project, Report, Task, TaskStep, Team
from query_optimizer import DjangoConnectionField, DjangoListField, DjangoObjectType, RelatedField
from tests.undine_port.factories import (
    CommentFactory,
    PersonFactory,
    ReportFactory,
    TaskFactory,
    TaskStepFactory,
    TeamFactory,
)

if TYPE_CHECKING:
    from django.db.models import Model

    from query_optimizer.typing import GQLInfo


# Differences to Undine:
# - Cursors here are offsets (`offset_to_cursor`), while Undine uses keyset cursors.
# - Undine `page_size` -> `max_limit` on `DjangoConnectionField`.
# - Top-level connections always run a `COUNT` query here, while Undine only counts if `totalCount`
#   is selected. Tests for top-level connections without `totalCount` expect one more query than in Undine.


class CountedConnection(relay.Connection):
    """Connection with `totalCount`, like Undine's `Connection`."""

    class Meta:
        abstract = True

    total_count = graphene.Int()

    def resolve_total_count(root: Any, info: GQLInfo, **kwargs: Any) -> int:
        return root.length


@dataclasses.dataclass
class Connection:
    """Marks a relation as a connection in `query_type`, like Undine's `Connection`."""

    type: type[DjangoObjectType]
    page_size: int | None = 100


def query_type(
    model: type[Model],
    *,
    name: str | None = None,
    node: bool = False,
    fields: list[str] | None = None,
    **relations: type[DjangoObjectType] | Connection,
) -> type[DjangoObjectType]:
    """Create an object type like an Undine `QueryType` with `auto=False` and the given fields."""
    attrs: dict[str, Any] = {}
    for field_name, value in relations.items():
        if isinstance(value, Connection):
            attrs[field_name] = DjangoConnectionField(value.type, max_limit=value.page_size)
            continue

        model_field = model._meta.get_field(field_name)
        if model_field.one_to_many or model_field.many_to_many:
            attrs[field_name] = DjangoListField(value)
        else:
            attrs[field_name] = RelatedField(value)

    meta = type(
        "Meta",
        (),
        {
            "model": model,
            "fields": [*(fields or []), *relations],
            "interfaces": (relay.Node,) if node else (),
            "connection_class": CountedConnection,
        },
    )
    return type(name or f"{model.__name__}Type", (DjangoObjectType,), {"Meta": meta, **attrs})


# Relay Node interface


@pytest.mark.django_db
def test_optimizer__relay__node(graphql) -> None:
    TaskType = query_type(Task, node=True, fields=["name"])

    class Query(graphene.ObjectType):
        node = relay.Node.Field()
        tasks = DjangoConnectionField(TaskType)

    graphql.schema = graphene.Schema(query=Query)

    task = TaskFactory.create(name="Task")

    global_id = to_global_id("TaskType", task.pk)

    query = """
        query NodeQuery($global_id: ID!) {
          node(id: $global_id) {
            __typename
            ... on TaskType {
              name
            }
          }
        }
    """

    response = graphql(query, variables={"global_id": global_id}, count_queries=True)

    assert response.has_errors is False, response.errors
    assert response.data == {
        "node": {
            "__typename": "TaskType",
            "name": "Task",
        },
    }

    response.assert_query_count(1)


@pytest.mark.django_db
def test_optimizer__relay__node__id_only(graphql) -> None:
    TaskType = query_type(Task, node=True, fields=["name"])

    class Query(graphene.ObjectType):
        node = relay.Node.Field()
        tasks = DjangoConnectionField(TaskType)

    graphql.schema = graphene.Schema(query=Query)

    task = TaskFactory.create(name="Task")

    global_id = to_global_id("TaskType", task.pk)

    query = """
        query NodeQuery($global_id: ID!) {
          node(id: $global_id) {
            __typename
            id
          }
        }
    """

    response = graphql(query, variables={"global_id": global_id}, count_queries=True)

    assert response.has_errors is False, response.errors
    assert response.data == {
        "node": {
            "__typename": "TaskType",
            "id": global_id,
        },
    }

    response.assert_query_count(1)


@pytest.mark.django_db
def test_optimizer__relay__node__joins(graphql) -> None:
    PersonType = query_type(Person, fields=["name"])

    ProjectType = query_type(Project, fields=["name"])

    TaskType = query_type(Task, node=True, fields=["name"], project=ProjectType, assignees=PersonType)

    class Query(graphene.ObjectType):
        node = relay.Node.Field()
        tasks = DjangoConnectionField(TaskType)

    graphql.schema = graphene.Schema(query=Query)

    task = TaskFactory.create(name="Task", project__name="Project", assignees__name="Assignee")

    global_id = to_global_id("TaskType", task.pk)

    query = """
        query NodeQuery($global_id: ID!) {
          node(id: $global_id) {
            __typename
            ... on TaskType {
              name
              project {
                name
              }
              assignees {
                name
              }
            }
          }
        }
    """

    response = graphql(query, variables={"global_id": global_id}, count_queries=True)

    assert response.has_errors is False, response.errors
    assert response.data == {
        "node": {
            "__typename": "TaskType",
            "name": "Task",
            "project": {"name": "Project"},
            "assignees": [{"name": "Assignee"}],
        },
    }

    response.assert_query_count(2)


# Relay Connections


@pytest.mark.django_db
def test_optimizer__relay__connection(graphql) -> None:
    TaskType = query_type(Task, node=True, fields=["name"])

    class Query(graphene.ObjectType):
        tasks = DjangoConnectionField(TaskType)

    graphql.schema = graphene.Schema(query=Query)

    TaskFactory.create(name="Task 1")
    TaskFactory.create(name="Task 2")
    TaskFactory.create(name="Task 3")

    query = """
        query {
          tasks {
            edges {
              node {
                name
              }
            }
          }
        }
    """

    response = graphql(query, count_queries=True)

    assert response.has_errors is False, response.errors
    assert response.data == {
        "tasks": {
            "edges": [
                {"node": {"name": "Task 1"}},
                {"node": {"name": "Task 2"}},
                {"node": {"name": "Task 3"}},
            ],
        },
    }

    response.assert_query_count(2)  # +1: top-level COUNT query


@pytest.mark.django_db
def test_optimizer__relay__connection__first(graphql) -> None:
    TaskType = query_type(Task, node=True, fields=["name"])

    class Query(graphene.ObjectType):
        tasks = DjangoConnectionField(TaskType)

    graphql.schema = graphene.Schema(query=Query)

    TaskFactory.create(name="Task 1")
    TaskFactory.create(name="Task 2")
    TaskFactory.create(name="Task 3")

    query = """
        query {
          tasks(first: 1) {
            edges {
              node {
                name
              }
            }
          }
        }
    """

    response = graphql(query, count_queries=True)

    assert response.has_errors is False, response.errors
    assert response.data == {
        "tasks": {
            "edges": [
                {"node": {"name": "Task 1"}},
            ],
        },
    }

    response.assert_query_count(2)  # +1: top-level COUNT query


@pytest.mark.django_db
def test_optimizer__relay__connection__last(graphql) -> None:
    TaskType = query_type(Task, node=True, fields=["name"])

    class Query(graphene.ObjectType):
        tasks = DjangoConnectionField(TaskType)

    graphql.schema = graphene.Schema(query=Query)

    TaskFactory.create(name="Task 1")
    TaskFactory.create(name="Task 2")
    TaskFactory.create(name="Task 3")

    query = """
        query {
          tasks(last: 1) {
            edges {
              node {
                name
              }
            }
          }
        }
    """

    response = graphql(query, count_queries=True)

    assert response.has_errors is False, response.errors
    assert response.data == {
        "tasks": {
            "edges": [
                {"node": {"name": "Task 3"}},
            ],
        },
    }

    response.assert_query_count(2)  # +1: top-level COUNT query


@pytest.mark.django_db
def test_optimizer__relay__connection__after(graphql) -> None:
    TaskType = query_type(Task, node=True, fields=["name"])

    class Query(graphene.ObjectType):
        tasks = DjangoConnectionField(TaskType)

    graphql.schema = graphene.Schema(query=Query)

    task_1 = TaskFactory.create(name="Task 1")
    TaskFactory.create(name="Task 2")
    TaskFactory.create(name="Task 3")

    query = """
        query ($after: String!) {
          tasks(after: $after) {
            edges {
              node {
                name
              }
            }
          }
        }
    """

    response = graphql(query, variables={"after": offset_to_cursor(0)}, count_queries=True)

    assert response.has_errors is False, response.errors
    assert response.data == {
        "tasks": {
            "edges": [
                {"node": {"name": "Task 2"}},
                {"node": {"name": "Task 3"}},
            ],
        },
    }

    response.assert_query_count(2)  # +1: top-level COUNT query


@pytest.mark.django_db
def test_optimizer__relay__connection__before(graphql) -> None:
    TaskType = query_type(Task, node=True, fields=["name"])

    class Query(graphene.ObjectType):
        tasks = DjangoConnectionField(TaskType)

    graphql.schema = graphene.Schema(query=Query)

    TaskFactory.create(name="Task 1")
    TaskFactory.create(name="Task 2")
    task_3 = TaskFactory.create(name="Task 3")

    query = """
        query ($before: String!) {
          tasks(before: $before) {
            edges {
              node {
                name
              }
            }
          }
        }
    """

    response = graphql(query, variables={"before": offset_to_cursor(2)}, count_queries=True)

    assert response.has_errors is False, response.errors
    assert response.data == {
        "tasks": {
            "edges": [
                {"node": {"name": "Task 1"}},
                {"node": {"name": "Task 2"}},
            ],
        },
    }

    response.assert_query_count(2)  # +1: top-level COUNT query


@pytest.mark.django_db
def test_optimizer__relay__connection__connection_info(graphql) -> None:
    TaskType = query_type(Task, node=True, fields=["name"])

    class Query(graphene.ObjectType):
        tasks = DjangoConnectionField(TaskType)

    graphql.schema = graphene.Schema(query=Query)

    task_1 = TaskFactory.create(name="Task 1")
    task_2 = TaskFactory.create(name="Task 2")
    task_3 = TaskFactory.create(name="Task 3")

    query = """
        query {
          tasks {
            totalCount
            pageInfo {
              hasNextPage
              hasPreviousPage
              startCursor
              endCursor
            }
            edges {
              cursor
              node {
                name
              }
            }
          }
        }
    """

    response = graphql(query, count_queries=True)

    assert response.has_errors is False, response.errors
    assert response.data == {
        "tasks": {
            "totalCount": 3,
            "pageInfo": {
                "hasNextPage": False,
                "hasPreviousPage": False,
                "startCursor": offset_to_cursor(0),
                "endCursor": offset_to_cursor(2),
            },
            "edges": [
                {
                    "cursor": offset_to_cursor(0),
                    "node": {
                        "name": "Task 1",
                    },
                },
                {
                    "cursor": offset_to_cursor(1),
                    "node": {
                        "name": "Task 2",
                    },
                },
                {
                    "cursor": offset_to_cursor(2),
                    "node": {
                        "name": "Task 3",
                    },
                },
            ],
        },
    }

    response.assert_query_count(2)


@pytest.mark.django_db
def test_optimizer__relay__connection__no_page_size(graphql) -> None:
    TaskType = query_type(Task, node=True, fields=["name"])

    class Query(graphene.ObjectType):
        tasks = DjangoConnectionField(TaskType, max_limit=None)

    graphql.schema = graphene.Schema(query=Query)

    TaskFactory.create(name="Task 1")
    TaskFactory.create(name="Task 2")
    TaskFactory.create(name="Task 3")

    query = """
        query {
          tasks {
            edges {
              node {
                name
              }
            }
          }
        }
    """

    response = graphql(query, count_queries=True)

    assert response.has_errors is False, response.errors
    assert response.data == {
        "tasks": {
            "edges": [
                {"node": {"name": "Task 1"}},
                {"node": {"name": "Task 2"}},
                {"node": {"name": "Task 3"}},
            ],
        },
    }

    response.assert_query_count(2)  # +1: top-level COUNT query


@pytest.mark.django_db
def test_optimizer__relay__connection__no_page_size__first(graphql) -> None:
    TaskType = query_type(Task, node=True, fields=["name"])

    class Query(graphene.ObjectType):
        tasks = DjangoConnectionField(TaskType, max_limit=None)

    graphql.schema = graphene.Schema(query=Query)

    TaskFactory.create(name="Task 1")
    TaskFactory.create(name="Task 2")
    TaskFactory.create(name="Task 3")

    query = """
        query {
          tasks(first: 1) {
            edges {
              node {
                name
              }
            }
          }
        }
    """

    response = graphql(query, count_queries=True)

    assert response.has_errors is False, response.errors
    assert response.data == {
        "tasks": {
            "edges": [
                {"node": {"name": "Task 1"}},
            ],
        },
    }

    response.assert_query_count(2)  # +1: top-level COUNT query


@pytest.mark.django_db
def test_optimizer__relay__connection__no_page_size__last(graphql) -> None:
    TaskType = query_type(Task, node=True, fields=["name"])

    class Query(graphene.ObjectType):
        tasks = DjangoConnectionField(TaskType, max_limit=None)

    graphql.schema = graphene.Schema(query=Query)

    TaskFactory.create(name="Task 1")
    TaskFactory.create(name="Task 2")
    TaskFactory.create(name="Task 3")

    query = """
        query {
          tasks(last: 2) {
            edges {
              node {
                name
              }
            }
          }
        }
    """

    response = graphql(query, count_queries=True)

    assert response.has_errors is False, response.errors
    assert response.data == {
        "tasks": {
            "edges": [
                {"node": {"name": "Task 2"}},
                {"node": {"name": "Task 3"}},
            ],
        },
    }

    response.assert_query_count(2)  # +1: top-level COUNT query


@pytest.mark.django_db
def test_optimizer__relay__connection__page_size__has_next_page(graphql) -> None:
    TaskType = query_type(Task, node=True, fields=["name"])

    class Query(graphene.ObjectType):
        tasks = DjangoConnectionField(TaskType, max_limit=2)

    graphql.schema = graphene.Schema(query=Query)

    task_1 = TaskFactory.create(name="Task 1")
    task_2 = TaskFactory.create(name="Task 2")
    TaskFactory.create(name="Task 3")

    query = """
        query {
          tasks {
            totalCount
            pageInfo {
              hasNextPage
              hasPreviousPage
              startCursor
              endCursor
            }
            edges {
              cursor
              node {
                name
              }
            }
          }
        }
    """

    response = graphql(query, count_queries=True)

    assert response.has_errors is False, response.errors
    assert response.data == {
        "tasks": {
            "totalCount": 3,
            "pageInfo": {
                "hasNextPage": True,
                "hasPreviousPage": False,
                "startCursor": offset_to_cursor(0),
                "endCursor": offset_to_cursor(1),
            },
            "edges": [
                {
                    "cursor": offset_to_cursor(0),
                    "node": {
                        "name": "Task 1",
                    },
                },
                {
                    "cursor": offset_to_cursor(1),
                    "node": {
                        "name": "Task 2",
                    },
                },
            ],
        },
    }

    response.assert_query_count(2)


@pytest.mark.django_db
def test_optimizer__relay__connection__page_size__has_previous_page(graphql) -> None:
    TaskType = query_type(Task, node=True, fields=["name"])

    class Query(graphene.ObjectType):
        tasks = DjangoConnectionField(TaskType, max_limit=2)

    graphql.schema = graphene.Schema(query=Query)

    task_1 = TaskFactory.create(name="Task 1")
    task_2 = TaskFactory.create(name="Task 2")
    task_3 = TaskFactory.create(name="Task 3")

    query = """
        query ($after: String!) {
          tasks(after: $after) {
            totalCount
            pageInfo {
              hasNextPage
              hasPreviousPage
              startCursor
              endCursor
            }
            edges {
              cursor
              node {
                name
              }
            }
          }
        }
    """

    response = graphql(query, variables={"after": offset_to_cursor(0)}, count_queries=True)

    assert response.has_errors is False, response.errors
    assert response.data == {
        "tasks": {
            "totalCount": 3,
            "pageInfo": {
                "hasNextPage": False,
                "hasPreviousPage": True,
                "startCursor": offset_to_cursor(1),
                "endCursor": offset_to_cursor(2),
            },
            "edges": [
                {
                    "cursor": offset_to_cursor(1),
                    "node": {
                        "name": "Task 2",
                    },
                },
                {
                    "cursor": offset_to_cursor(2),
                    "node": {
                        "name": "Task 3",
                    },
                },
            ],
        },
    }

    response.assert_query_count(2)


@pytest.mark.django_db
def test_optimizer__relay__connection__joins(graphql) -> None:
    PersonType = query_type(Person, fields=["name"])

    ProjectType = query_type(Project, fields=["name"])

    TaskType = query_type(Task, node=True, fields=["name"], project=ProjectType, assignees=PersonType)

    class Query(graphene.ObjectType):
        tasks = DjangoConnectionField(TaskType)

    graphql.schema = graphene.Schema(query=Query)

    TaskFactory.create(name="Task 1", project__name="Project 1", assignees__name="Assignee 1")
    TaskFactory.create(name="Task 2", project__name="Project 2", assignees__name="Assignee 2")
    TaskFactory.create(name="Task 3", project__name="Project 3", assignees__name="Assignee 3")

    query = """
        query {
          tasks {
            edges {
              node {
                name
                project {
                  name
                }
                assignees {
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
        "tasks": {
            "edges": [
                {
                    "node": {
                        "name": "Task 1",
                        "project": {"name": "Project 1"},
                        "assignees": [{"name": "Assignee 1"}],
                    },
                },
                {
                    "node": {
                        "name": "Task 2",
                        "project": {"name": "Project 2"},
                        "assignees": [{"name": "Assignee 2"}],
                    },
                },
                {
                    "node": {
                        "name": "Task 3",
                        "project": {"name": "Project 3"},
                        "assignees": [{"name": "Assignee 3"}],
                    },
                },
            ],
        },
    }

    response.assert_query_count(3)  # +1: top-level COUNT query


@pytest.mark.django_db
def test_optimizer__relay__connection__joins__connection_info(graphql) -> None:
    PersonType = query_type(Person, fields=["name"])

    ProjectType = query_type(Project, fields=["name"])

    TaskType = query_type(Task, node=True, fields=["name"], project=ProjectType, assignees=PersonType)

    class Query(graphene.ObjectType):
        tasks = DjangoConnectionField(TaskType)

    graphql.schema = graphene.Schema(query=Query)

    task_1 = TaskFactory.create(name="Task 1", project__name="Project 1", assignees__name="Assignee 1")
    task_2 = TaskFactory.create(name="Task 2", project__name="Project 2", assignees__name="Assignee 2")
    task_3 = TaskFactory.create(name="Task 3", project__name="Project 3", assignees__name="Assignee 3")

    query = """
        query {
          tasks {
            totalCount
            pageInfo {
              hasNextPage
              hasPreviousPage
              startCursor
              endCursor
            }
            edges {
              cursor
              node {
                name
                project {
                  name
                }
                assignees {
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
        "tasks": {
            "totalCount": 3,
            "pageInfo": {
                "hasNextPage": False,
                "hasPreviousPage": False,
                "startCursor": offset_to_cursor(0),
                "endCursor": offset_to_cursor(2),
            },
            "edges": [
                {
                    "cursor": offset_to_cursor(0),
                    "node": {
                        "name": "Task 1",
                        "project": {"name": "Project 1"},
                        "assignees": [{"name": "Assignee 1"}],
                    },
                },
                {
                    "cursor": offset_to_cursor(1),
                    "node": {
                        "name": "Task 2",
                        "project": {"name": "Project 2"},
                        "assignees": [{"name": "Assignee 2"}],
                    },
                },
                {
                    "cursor": offset_to_cursor(2),
                    "node": {
                        "name": "Task 3",
                        "project": {"name": "Project 3"},
                        "assignees": [{"name": "Assignee 3"}],
                    },
                },
            ],
        },
    }

    response.assert_query_count(3)


@pytest.mark.django_db
def test_optimizer__relay__connection__total_count_in_fragment(graphql) -> None:
    TaskType = query_type(Task, node=True, fields=["name"])

    class Query(graphene.ObjectType):
        tasks = DjangoConnectionField(TaskType)

    graphql.schema = graphene.Schema(query=Query)

    TaskFactory.create(name="Task 1")
    TaskFactory.create(name="Task 2")
    TaskFactory.create(name="Task 3")

    query = """
        fragment TaskEdges on TaskTypeConnection {
          totalCount
          edges {
            node {
              name
            }
          }
        }

        query {
          tasks {
            ...TaskEdges
          }
        }
    """

    response = graphql(query, count_queries=True)

    assert response.has_errors is False, response.errors
    assert response.data == {
        "tasks": {
            "totalCount": 3,
            "edges": [
                {"node": {"name": "Task 1"}},
                {"node": {"name": "Task 2"}},
                {"node": {"name": "Task 3"}},
            ],
        },
    }

    response.assert_query_count(2)


@pytest.mark.django_db
def test_optimizer__relay__connection__different_ordering(graphql) -> None:
    class TaskOrderSet(OrderSet[Task]): ...

    class TaskType(QueryType[Task], auto=False, interfaces=[Node], orderset=TaskOrderSet):
        name = Field()

    class Query(graphene.ObjectType):
        tasks = DjangoConnectionField(TaskType)

    graphql.schema = graphene.Schema(query=Query)

    TaskFactory.create(name="Task 1")
    TaskFactory.create(name="Task 2")
    TaskFactory.create(name="Task 3")

    query = """
        query {
          tasks(orderBy: nameDesc, first: 2) {
            edges {
              node {
                name
              }
            }
          }
        }
    """

    response = graphql(query, count_queries=True)

    assert response.has_errors is False, response.errors
    assert response.data == {
        "tasks": {
            "edges": [
                {"node": {"name": "Task 3"}},
                {"node": {"name": "Task 2"}},
            ],
        },
    }

    response.assert_query_count(1)


@pytest.mark.django_db
def test_optimizer__relay__connection__only_total_count(graphql) -> None:
    TaskType = query_type(Task, node=True, fields=["name"])

    class Query(graphene.ObjectType):
        tasks = DjangoConnectionField(TaskType)

    graphql.schema = graphene.Schema(query=Query)

    TaskFactory.create(name="Task 1")
    TaskFactory.create(name="Task 2")
    TaskFactory.create(name="Task 3")

    query = """
        query {
          tasks {
            totalCount
          }
        }
    """

    response = graphql(query, count_queries=True)

    assert response.has_errors is False, response.errors
    assert response.data == {
        "tasks": {
            "totalCount": 3,
        },
    }

    response.assert_query_count(2)


@pytest.mark.django_db
def test_optimizer__relay__connection__only_cursor(graphql) -> None:
    TaskType = query_type(Task, node=True, fields=["name"])

    class Query(graphene.ObjectType):
        tasks = DjangoConnectionField(TaskType)

    graphql.schema = graphene.Schema(query=Query)

    task_1 = TaskFactory.create(name="Task 1")
    task_2 = TaskFactory.create(name="Task 2")
    task_3 = TaskFactory.create(name="Task 3")

    query = """
        query {
          tasks {
            edges {
              cursor
            }
          }
        }
    """

    response = graphql(query, count_queries=True)

    assert response.has_errors is False, response.errors
    assert response.data == {
        "tasks": {
            "edges": [
                {"cursor": offset_to_cursor(0)},
                {"cursor": offset_to_cursor(1)},
                {"cursor": offset_to_cursor(2)},
            ],
        },
    }

    response.assert_query_count(2)  # +1: top-level COUNT query


@pytest.mark.django_db
def test_optimizer__relay__connection__alias(graphql) -> None:
    TaskType = query_type(Task, node=True, fields=["name"])

    class Query(graphene.ObjectType):
        tasks = DjangoConnectionField(TaskType)

    graphql.schema = graphene.Schema(query=Query)

    TaskFactory.create(name="Task 1")
    TaskFactory.create(name="Task 2")
    TaskFactory.create(name="Task 3")

    query = """
        query {
          tasks {
            edges {
              node {
                name
              }
            }
          }
          pagedTasks: tasks(first: 1) {
            edges {
              node {
                name
              }
            }
          }
        }
    """

    response = graphql(query, count_queries=True)

    assert response.has_errors is False, response.errors
    assert response.data == {
        "tasks": {
            "edges": [
                {"node": {"name": "Task 1"}},
                {"node": {"name": "Task 2"}},
                {"node": {"name": "Task 3"}},
            ],
        },
        "pagedTasks": {
            "edges": [
                {"node": {"name": "Task 1"}},
            ],
        },
    }

    response.assert_query_count(4)  # +2: 2 top-level COUNT queries


@pytest.mark.django_db
def test_optimizer__relay__connection__has_next_page(graphql) -> None:
    # graphene-django connections require the `Node` interface.
    TaskType = query_type(Task, node=True, fields=["name"])

    class Query(graphene.ObjectType):
        tasks = DjangoConnectionField(TaskType)

    graphql.schema = graphene.Schema(query=Query)

    TaskFactory.create(name="Task 1")

    query = """
        query {
          tasks {
            pageInfo {
              hasNextPage
            }
          }
        }
    """

    response = graphql(query)
    assert response.has_errors is False, response.errors
    assert "hasNextPage" in response.data["tasks"]["pageInfo"]


@pytest.mark.django_db
def test_optimizer__relay__connection__total_count__no_pagination(graphql) -> None:
    # graphene-django connections require the `Node` interface.
    TaskType = query_type(Task, node=True, fields=["name"])

    class Query(graphene.ObjectType):
        tasks = DjangoConnectionField(TaskType)

    graphql.schema = graphene.Schema(query=Query)

    TaskFactory.create(name="T1")
    TaskFactory.create(name="T2")

    query = """
        query {
          tasks {
            totalCount
            edges {
              node {
                name
              }
            }
          }
        }
    """

    response = graphql(query)
    assert response.has_errors is False, response.errors
    assert response.data["tasks"]["totalCount"] == 2


# Nested Relay Connections


@pytest.mark.django_db
def test_optimizer__relay__nested_connection__many_to_many__forward(graphql) -> None:
    PersonType = query_type(Person, node=True, fields=["name"])

    TaskType = query_type(Task, node=True, fields=["name"], assignees=Connection(PersonType))

    class Query(graphene.ObjectType):
        tasks = DjangoConnectionField(TaskType)

    graphql.schema = graphene.Schema(query=Query)

    person_1 = PersonFactory.create(name="Assignee 1")
    person_2 = PersonFactory.create(name="Assignee 2")
    person_3 = PersonFactory.create(name="Assignee 3")
    person_4 = PersonFactory.create(name="Assignee 4")
    person_5 = PersonFactory.create(name="Assignee 5")

    TaskFactory.create(name="Task 1", assignees=[person_1, person_2, person_3])
    TaskFactory.create(name="Task 2", assignees=[person_3, person_4])
    TaskFactory.create(name="Task 3", assignees=[person_5])

    query = """
        query {
          tasks {
            edges {
              node {
                name
                assignees {
                  edges {
                    node {
                      name
                    }
                  }
                }
              }
            }
          }
        }
    """

    response = graphql(query, count_queries=True)

    assert response.has_errors is False, response.errors
    assert response.data == {
        "tasks": {
            "edges": [
                {
                    "node": {
                        "name": "Task 1",
                        "assignees": {
                            "edges": [
                                {"node": {"name": "Assignee 1"}},
                                {"node": {"name": "Assignee 2"}},
                                {"node": {"name": "Assignee 3"}},
                            ],
                        },
                    },
                },
                {
                    "node": {
                        "name": "Task 2",
                        "assignees": {
                            "edges": [
                                {"node": {"name": "Assignee 3"}},
                                {"node": {"name": "Assignee 4"}},
                            ],
                        },
                    },
                },
                {
                    "node": {
                        "name": "Task 3",
                        "assignees": {
                            "edges": [
                                {"node": {"name": "Assignee 5"}},
                            ],
                        },
                    },
                },
            ],
        },
    }

    response.assert_query_count(3)  # +1: top-level COUNT query


@pytest.mark.django_db
def test_optimizer__relay__nested_connection__many_to_many__reverse(graphql) -> None:
    ReportType = query_type(Report, node=True, fields=["name"])

    TaskType = query_type(Task, node=True, fields=["name"], reports=Connection(ReportType))

    class Query(graphene.ObjectType):
        tasks = DjangoConnectionField(TaskType)

    graphql.schema = graphene.Schema(query=Query)

    report_1 = ReportFactory.create(name="Report 1")
    report_2 = ReportFactory.create(name="Report 2")
    report_3 = ReportFactory.create(name="Report 3")
    report_4 = ReportFactory.create(name="Report 4")
    report_5 = ReportFactory.create(name="Report 5")

    TaskFactory.create(name="Task 1", reports=[report_1, report_2, report_3])
    TaskFactory.create(name="Task 2", reports=[report_3, report_4])
    TaskFactory.create(name="Task 3", reports=[report_5])

    query = """
        query {
          tasks {
            edges {
              node {
                name
                reports {
                  edges {
                    node {
                      name
                    }
                  }
                }
              }
            }
          }
        }
    """

    response = graphql(query, count_queries=True)

    # Without an `OrderSet`, results are ordered by primary key, which is a random UUID for `Report`.
    def expected_reports(*reports: Report) -> dict:
        names = [report.name for report in sorted(reports, key=lambda report: report.pk)]
        return {"edges": [{"node": {"name": name}} for name in names]}

    assert response.has_errors is False, response.errors
    assert response.data == {
        "tasks": {
            "edges": [
                {
                    "node": {
                        "name": "Task 1",
                        "reports": expected_reports(report_1, report_2, report_3),
                    },
                },
                {
                    "node": {
                        "name": "Task 2",
                        "reports": expected_reports(report_3, report_4),
                    },
                },
                {
                    "node": {
                        "name": "Task 3",
                        "reports": expected_reports(report_5),
                    },
                },
            ],
        },
    }

    response.assert_query_count(3)  # +1: top-level COUNT query


@pytest.mark.django_db
def test_optimizer__relay__nested_connection__first(graphql) -> None:
    PersonType = query_type(Person, node=True, fields=["name"])

    TaskType = query_type(Task, node=True, fields=["name"], assignees=Connection(PersonType))

    class Query(graphene.ObjectType):
        tasks = DjangoConnectionField(TaskType)

    graphql.schema = graphene.Schema(query=Query)

    person_1 = PersonFactory.create(name="Assignee 1")
    person_2 = PersonFactory.create(name="Assignee 2")
    person_3 = PersonFactory.create(name="Assignee 3")
    person_4 = PersonFactory.create(name="Assignee 4")
    person_5 = PersonFactory.create(name="Assignee 5")

    TaskFactory.create(name="Task 1", assignees=[person_1, person_2, person_3])
    TaskFactory.create(name="Task 2", assignees=[person_3, person_4])
    TaskFactory.create(name="Task 3", assignees=[person_5])

    query = """
        query {
          tasks {
            edges {
              node {
                name
                assignees(first: 1) {
                  edges {
                    node {
                      name
                    }
                  }
                }
              }
            }
          }
        }
    """

    response = graphql(query, count_queries=True)

    assert response.has_errors is False, response.errors
    assert response.data == {
        "tasks": {
            "edges": [
                {
                    "node": {
                        "name": "Task 1",
                        "assignees": {
                            "edges": [
                                {"node": {"name": "Assignee 1"}},
                            ],
                        },
                    },
                },
                {
                    "node": {
                        "name": "Task 2",
                        "assignees": {
                            "edges": [
                                {"node": {"name": "Assignee 3"}},
                            ],
                        },
                    },
                },
                {
                    "node": {
                        "name": "Task 3",
                        "assignees": {
                            "edges": [
                                {"node": {"name": "Assignee 5"}},
                            ],
                        },
                    },
                },
            ],
        },
    }

    response.assert_query_count(3)  # +1: top-level COUNT query


@pytest.mark.django_db
def test_optimizer__relay__nested_connection__last(graphql) -> None:
    PersonType = query_type(Person, node=True, fields=["name"])

    TaskType = query_type(Task, node=True, fields=["name"], assignees=Connection(PersonType))

    class Query(graphene.ObjectType):
        tasks = DjangoConnectionField(TaskType)

    graphql.schema = graphene.Schema(query=Query)

    person_1 = PersonFactory.create(name="Assignee 1")
    person_2 = PersonFactory.create(name="Assignee 2")
    person_3 = PersonFactory.create(name="Assignee 3")
    person_4 = PersonFactory.create(name="Assignee 4")
    person_5 = PersonFactory.create(name="Assignee 5")

    TaskFactory.create(name="Task 1", assignees=[person_1, person_2, person_3])
    TaskFactory.create(name="Task 2", assignees=[person_3, person_4])
    TaskFactory.create(name="Task 3", assignees=[person_5])

    query = """
        query {
          tasks {
            edges {
              node {
                name
                assignees(last: 1) {
                  edges {
                    node {
                      name
                    }
                  }
                }
              }
            }
          }
        }
    """

    response = graphql(query, count_queries=True)

    assert response.has_errors is False, response.errors
    assert response.data == {
        "tasks": {
            "edges": [
                {
                    "node": {
                        "name": "Task 1",
                        "assignees": {
                            "edges": [
                                {"node": {"name": "Assignee 3"}},
                            ],
                        },
                    },
                },
                {
                    "node": {
                        "name": "Task 2",
                        "assignees": {
                            "edges": [
                                {"node": {"name": "Assignee 4"}},
                            ],
                        },
                    },
                },
                {
                    "node": {
                        "name": "Task 3",
                        "assignees": {
                            "edges": [
                                {"node": {"name": "Assignee 5"}},
                            ],
                        },
                    },
                },
            ],
        },
    }

    response.assert_query_count(3)  # +1: top-level COUNT query


@pytest.mark.django_db
def test_optimizer__relay__nested_connection__after(graphql) -> None:
    PersonType = query_type(Person, node=True, fields=["name"])

    TaskType = query_type(Task, node=True, fields=["name"], assignees=Connection(PersonType))

    class Query(graphene.ObjectType):
        tasks = DjangoConnectionField(TaskType)

    graphql.schema = graphene.Schema(query=Query)

    person_1 = PersonFactory.create(name="Assignee 1")
    person_2 = PersonFactory.create(name="Assignee 2")
    person_3 = PersonFactory.create(name="Assignee 3")
    person_4 = PersonFactory.create(name="Assignee 4")
    person_5 = PersonFactory.create(name="Assignee 5")

    TaskFactory.create(name="Task 1", assignees=[person_1, person_2, person_3])
    TaskFactory.create(name="Task 2", assignees=[person_3, person_4])
    TaskFactory.create(name="Task 3", assignees=[person_5])

    query = """
        query ($after: String!) {
          tasks {
            edges {
              node {
                name
                assignees(after: $after) {
                  edges {
                    node {
                      name
                    }
                  }
                }
              }
            }
          }
        }
    """

    response = graphql(query, variables={"after": offset_to_cursor(0)}, count_queries=True)

    # A cursor points to a row rather than an index, so each parent's list starts
    # from the first row ordered after that row instead of from the same offset.
    assert response.has_errors is False, response.errors
    assert response.data == {
        "tasks": {
            "edges": [
                {
                    "node": {
                        "name": "Task 1",
                        "assignees": {
                            "edges": [
                                {"node": {"name": "Assignee 2"}},
                                {"node": {"name": "Assignee 3"}},
                            ],
                        },
                    },
                },
                {
                    "node": {
                        "name": "Task 2",
                        "assignees": {
                            "edges": [
                                {"node": {"name": "Assignee 3"}},
                                {"node": {"name": "Assignee 4"}},
                            ],
                        },
                    },
                },
                {
                    "node": {
                        "name": "Task 3",
                        "assignees": {
                            "edges": [
                                {"node": {"name": "Assignee 5"}},
                            ],
                        },
                    },
                },
            ],
        },
    }

    response.assert_query_count(2)


@pytest.mark.django_db
def test_optimizer__relay__nested_connection__before(graphql) -> None:
    PersonType = query_type(Person, node=True, fields=["name"])

    TaskType = query_type(Task, node=True, fields=["name"], assignees=Connection(PersonType))

    class Query(graphene.ObjectType):
        tasks = DjangoConnectionField(TaskType)

    graphql.schema = graphene.Schema(query=Query)

    person_1 = PersonFactory.create(name="Assignee 1")
    person_2 = PersonFactory.create(name="Assignee 2")
    person_3 = PersonFactory.create(name="Assignee 3")
    person_4 = PersonFactory.create(name="Assignee 4")
    person_5 = PersonFactory.create(name="Assignee 5")

    TaskFactory.create(name="Task 1", assignees=[person_1, person_2, person_3])
    TaskFactory.create(name="Task 2", assignees=[person_3, person_4])
    TaskFactory.create(name="Task 3", assignees=[person_5])

    query = """
        query ($before: String!) {
          tasks {
            edges {
              node {
                name
                assignees(before: $before) {
                  edges {
                    node {
                      name
                    }
                  }
                }
              }
            }
          }
        }
    """

    response = graphql(query, variables={"before": offset_to_cursor(2)}, count_queries=True)

    # A cursor points to a row rather than an index, so each parent's list stops
    # at the last row ordered before that row instead of at the same offset.
    assert response.has_errors is False, response.errors
    assert response.data == {
        "tasks": {
            "edges": [
                {
                    "node": {
                        "name": "Task 1",
                        "assignees": {
                            "edges": [
                                {"node": {"name": "Assignee 1"}},
                                {"node": {"name": "Assignee 2"}},
                            ],
                        },
                    },
                },
                {
                    "node": {
                        "name": "Task 2",
                        "assignees": {
                            "edges": [],
                        },
                    },
                },
                {
                    "node": {
                        "name": "Task 3",
                        "assignees": {
                            "edges": [],
                        },
                    },
                },
            ],
        },
    }

    response.assert_query_count(2)


@pytest.mark.django_db
def test_optimizer__relay__nested_connection__connection_info(graphql) -> None:
    PersonType = query_type(Person, node=True, fields=["name"])

    TaskType = query_type(Task, node=True, fields=["name"], assignees=Connection(PersonType))

    class Query(graphene.ObjectType):
        tasks = DjangoConnectionField(TaskType)

    graphql.schema = graphene.Schema(query=Query)

    person_1 = PersonFactory.create(name="Assignee 1")
    person_2 = PersonFactory.create(name="Assignee 2")
    person_3 = PersonFactory.create(name="Assignee 3")
    person_4 = PersonFactory.create(name="Assignee 4")
    person_5 = PersonFactory.create(name="Assignee 5")

    TaskFactory.create(name="Task 1", assignees=[person_1, person_2, person_3])
    TaskFactory.create(name="Task 2", assignees=[person_3, person_4])
    TaskFactory.create(name="Task 3", assignees=[person_5])

    query = """
        query {
          tasks {
            edges {
              node {
                name
                assignees {
                  totalCount
                  pageInfo {
                    hasNextPage
                    hasPreviousPage
                    startCursor
                    endCursor
                  }
                  edges {
                    cursor
                    node {
                      name
                    }
                  }
                }
              }
            }
          }
        }
    """

    response = graphql(query, count_queries=True)

    assert response.has_errors is False, response.errors
    assert response.data == {
        "tasks": {
            "edges": [
                {
                    "node": {
                        "name": "Task 1",
                        "assignees": {
                            "totalCount": 3,
                            "pageInfo": {
                                "hasNextPage": False,
                                "hasPreviousPage": False,
                                "startCursor": offset_to_cursor(0),
                                "endCursor": offset_to_cursor(2),
                            },
                            "edges": [
                                {
                                    "cursor": offset_to_cursor(0),
                                    "node": {"name": "Assignee 1"},
                                },
                                {
                                    "cursor": offset_to_cursor(1),
                                    "node": {"name": "Assignee 2"},
                                },
                                {
                                    "cursor": offset_to_cursor(2),
                                    "node": {"name": "Assignee 3"},
                                },
                            ],
                        },
                    },
                },
                {
                    "node": {
                        "name": "Task 2",
                        "assignees": {
                            "totalCount": 2,
                            "pageInfo": {
                                "hasNextPage": False,
                                "hasPreviousPage": False,
                                "startCursor": offset_to_cursor(2),
                                "endCursor": offset_to_cursor(3),
                            },
                            "edges": [
                                {
                                    "cursor": offset_to_cursor(2),
                                    "node": {"name": "Assignee 3"},
                                },
                                {
                                    "cursor": offset_to_cursor(3),
                                    "node": {"name": "Assignee 4"},
                                },
                            ],
                        },
                    },
                },
                {
                    "node": {
                        "name": "Task 3",
                        "assignees": {
                            "totalCount": 1,
                            "pageInfo": {
                                "hasNextPage": False,
                                "hasPreviousPage": False,
                                "startCursor": offset_to_cursor(4),
                                "endCursor": offset_to_cursor(4),
                            },
                            "edges": [
                                {
                                    "cursor": offset_to_cursor(4),
                                    "node": {"name": "Assignee 5"},
                                },
                            ],
                        },
                    },
                },
            ],
        },
    }

    response.assert_query_count(2)


@pytest.mark.django_db
def test_optimizer__relay__nested_connection__no_page_size(graphql) -> None:
    PersonType = query_type(Person, node=True, fields=["name"])

    TaskType = query_type(Task, node=True, fields=["name"], assignees=Connection(PersonType, page_size=None))

    class Query(graphene.ObjectType):
        tasks = DjangoConnectionField(TaskType)

    graphql.schema = graphene.Schema(query=Query)

    person_1 = PersonFactory.create(name="Assignee 1")
    person_2 = PersonFactory.create(name="Assignee 2")
    person_3 = PersonFactory.create(name="Assignee 3")
    person_4 = PersonFactory.create(name="Assignee 4")
    person_5 = PersonFactory.create(name="Assignee 5")

    TaskFactory.create(name="Task 1", assignees=[person_1, person_2, person_3])
    TaskFactory.create(name="Task 2", assignees=[person_3, person_4])
    TaskFactory.create(name="Task 3", assignees=[person_5])

    query = """
        query {
          tasks {
            edges {
              node {
                name
                assignees {
                  edges {
                    node {
                      name
                    }
                  }
                }
              }
            }
          }
        }
    """

    response = graphql(query, count_queries=True)

    assert response.has_errors is False, response.errors
    assert response.data == {
        "tasks": {
            "edges": [
                {
                    "node": {
                        "name": "Task 1",
                        "assignees": {
                            "edges": [
                                {"node": {"name": "Assignee 1"}},
                                {"node": {"name": "Assignee 2"}},
                                {"node": {"name": "Assignee 3"}},
                            ],
                        },
                    },
                },
                {
                    "node": {
                        "name": "Task 2",
                        "assignees": {
                            "edges": [
                                {"node": {"name": "Assignee 3"}},
                                {"node": {"name": "Assignee 4"}},
                            ],
                        },
                    },
                },
                {
                    "node": {
                        "name": "Task 3",
                        "assignees": {
                            "edges": [
                                {"node": {"name": "Assignee 5"}},
                            ],
                        },
                    },
                },
            ],
        },
    }

    response.assert_query_count(3)  # +1: top-level COUNT query


@pytest.mark.django_db
def test_optimizer__relay__nested_connection__no_page_size__first(graphql) -> None:
    PersonType = query_type(Person, node=True, fields=["name"])

    TaskType = query_type(Task, node=True, fields=["name"], assignees=Connection(PersonType, page_size=None))

    class Query(graphene.ObjectType):
        tasks = DjangoConnectionField(TaskType)

    graphql.schema = graphene.Schema(query=Query)

    person_1 = PersonFactory.create(name="Assignee 1")
    person_2 = PersonFactory.create(name="Assignee 2")
    person_3 = PersonFactory.create(name="Assignee 3")
    person_4 = PersonFactory.create(name="Assignee 4")
    person_5 = PersonFactory.create(name="Assignee 5")

    TaskFactory.create(name="Task 1", assignees=[person_1, person_2, person_3])
    TaskFactory.create(name="Task 2", assignees=[person_3, person_4])
    TaskFactory.create(name="Task 3", assignees=[person_5])

    query = """
        query {
          tasks {
            edges {
              node {
                name
                assignees(first: 1) {
                  edges {
                    node {
                      name
                    }
                  }
                }
              }
            }
          }
        }
    """

    response = graphql(query, count_queries=True)

    assert response.has_errors is False, response.errors
    assert response.data == {
        "tasks": {
            "edges": [
                {
                    "node": {
                        "name": "Task 1",
                        "assignees": {
                            "edges": [
                                {"node": {"name": "Assignee 1"}},
                            ],
                        },
                    },
                },
                {
                    "node": {
                        "name": "Task 2",
                        "assignees": {
                            "edges": [
                                {"node": {"name": "Assignee 3"}},
                            ],
                        },
                    },
                },
                {
                    "node": {
                        "name": "Task 3",
                        "assignees": {
                            "edges": [
                                {"node": {"name": "Assignee 5"}},
                            ],
                        },
                    },
                },
            ],
        },
    }

    response.assert_query_count(3)  # +1: top-level COUNT query


@pytest.mark.django_db
def test_optimizer__relay__nested_connection__no_page_size__last(graphql) -> None:
    PersonType = query_type(Person, node=True, fields=["name"])

    TaskType = query_type(Task, node=True, fields=["name"], assignees=Connection(PersonType, page_size=None))

    class Query(graphene.ObjectType):
        tasks = DjangoConnectionField(TaskType)

    graphql.schema = graphene.Schema(query=Query)

    person_1 = PersonFactory.create(name="Assignee 1")
    person_2 = PersonFactory.create(name="Assignee 2")
    person_3 = PersonFactory.create(name="Assignee 3")
    person_4 = PersonFactory.create(name="Assignee 4")
    person_5 = PersonFactory.create(name="Assignee 5")

    TaskFactory.create(name="Task 1", assignees=[person_1, person_2, person_3])
    TaskFactory.create(name="Task 2", assignees=[person_3, person_4])
    TaskFactory.create(name="Task 3", assignees=[person_5])

    query = """
        query {
          tasks {
            edges {
              node {
                name
                assignees(last: 1) {
                  edges {
                    node {
                      name
                    }
                  }
                }
              }
            }
          }
        }
    """

    response = graphql(query, count_queries=True)

    assert response.has_errors is False, response.errors
    assert response.data == {
        "tasks": {
            "edges": [
                {
                    "node": {
                        "name": "Task 1",
                        "assignees": {
                            "edges": [
                                {"node": {"name": "Assignee 3"}},
                            ],
                        },
                    },
                },
                {
                    "node": {
                        "name": "Task 2",
                        "assignees": {
                            "edges": [
                                {"node": {"name": "Assignee 4"}},
                            ],
                        },
                    },
                },
                {
                    "node": {
                        "name": "Task 3",
                        "assignees": {
                            "edges": [
                                {"node": {"name": "Assignee 5"}},
                            ],
                        },
                    },
                },
            ],
        },
    }

    response.assert_query_count(3)  # +1: top-level COUNT query


@pytest.mark.django_db
def test_optimizer__relay__nested_connection__page_size__has_next_page(graphql) -> None:
    PersonType = query_type(Person, node=True, fields=["name"])

    TaskType = query_type(Task, node=True, fields=["name"], assignees=Connection(PersonType, page_size=2))

    class Query(graphene.ObjectType):
        tasks = DjangoConnectionField(TaskType)

    graphql.schema = graphene.Schema(query=Query)

    person_1 = PersonFactory.create(name="Assignee 1")
    person_2 = PersonFactory.create(name="Assignee 2")
    person_3 = PersonFactory.create(name="Assignee 3")
    person_4 = PersonFactory.create(name="Assignee 4")
    person_5 = PersonFactory.create(name="Assignee 5")

    TaskFactory.create(name="Task 1", assignees=[person_1, person_2, person_3])
    TaskFactory.create(name="Task 2", assignees=[person_3, person_4])
    TaskFactory.create(name="Task 3", assignees=[person_5])

    query = """
        query {
          tasks {
            edges {
              node {
                name
                assignees {
                  totalCount
                  pageInfo {
                    hasNextPage
                    hasPreviousPage
                    startCursor
                    endCursor
                  }
                  edges {
                    cursor
                    node {
                      name
                    }
                  }
                }
              }
            }
          }
        }
    """

    response = graphql(query, count_queries=True)

    assert response.has_errors is False, response.errors
    assert response.data == {
        "tasks": {
            "edges": [
                {
                    "node": {
                        "name": "Task 1",
                        "assignees": {
                            "totalCount": 3,
                            "pageInfo": {
                                "hasNextPage": True,
                                "hasPreviousPage": False,
                                "startCursor": offset_to_cursor(0),
                                "endCursor": offset_to_cursor(1),
                            },
                            "edges": [
                                {
                                    "cursor": offset_to_cursor(0),
                                    "node": {"name": "Assignee 1"},
                                },
                                {
                                    "cursor": offset_to_cursor(1),
                                    "node": {"name": "Assignee 2"},
                                },
                            ],
                        },
                    },
                },
                {
                    "node": {
                        "name": "Task 2",
                        "assignees": {
                            "totalCount": 2,
                            "pageInfo": {
                                "hasNextPage": False,
                                "hasPreviousPage": False,
                                "startCursor": offset_to_cursor(2),
                                "endCursor": offset_to_cursor(3),
                            },
                            "edges": [
                                {
                                    "cursor": offset_to_cursor(2),
                                    "node": {"name": "Assignee 3"},
                                },
                                {
                                    "cursor": offset_to_cursor(3),
                                    "node": {"name": "Assignee 4"},
                                },
                            ],
                        },
                    },
                },
                {
                    "node": {
                        "name": "Task 3",
                        "assignees": {
                            "totalCount": 1,
                            "pageInfo": {
                                "hasNextPage": False,
                                "hasPreviousPage": False,
                                "startCursor": offset_to_cursor(4),
                                "endCursor": offset_to_cursor(4),
                            },
                            "edges": [
                                {
                                    "cursor": offset_to_cursor(4),
                                    "node": {"name": "Assignee 5"},
                                },
                            ],
                        },
                    },
                },
            ],
        },
    }

    response.assert_query_count(2)


@pytest.mark.django_db
def test_optimizer__relay__nested_connection__page_size__has_previous_page(graphql) -> None:
    PersonType = query_type(Person, node=True, fields=["name"])

    TaskType = query_type(Task, node=True, fields=["name"], assignees=Connection(PersonType, page_size=2))

    class Query(graphene.ObjectType):
        tasks = DjangoConnectionField(TaskType)

    graphql.schema = graphene.Schema(query=Query)

    person_1 = PersonFactory.create(name="Assignee 1")
    person_2 = PersonFactory.create(name="Assignee 2")
    person_3 = PersonFactory.create(name="Assignee 3")
    person_4 = PersonFactory.create(name="Assignee 4")
    person_5 = PersonFactory.create(name="Assignee 5")

    TaskFactory.create(name="Task 1", assignees=[person_1, person_2, person_3])
    TaskFactory.create(name="Task 2", assignees=[person_3, person_4])
    TaskFactory.create(name="Task 3", assignees=[person_5])

    query = """
        query ($after: String!) {
          tasks {
            edges {
              node {
                name
                assignees(after: $after) {
                  totalCount
                  pageInfo {
                    hasNextPage
                    hasPreviousPage
                    startCursor
                    endCursor
                  }
                  edges {
                    cursor
                    node {
                      name
                    }
                  }
                }
              }
            }
          }
        }
    """

    response = graphql(query, variables={"after": offset_to_cursor(0)}, count_queries=True)

    # A cursor points to a row rather than an index, so each parent's list starts
    # from the first row ordered after that row instead of from the same offset.
    assert response.has_errors is False, response.errors
    assert response.data == {
        "tasks": {
            "edges": [
                {
                    "node": {
                        "name": "Task 1",
                        "assignees": {
                            "totalCount": 3,
                            "pageInfo": {
                                "hasNextPage": False,
                                "hasPreviousPage": True,
                                "startCursor": offset_to_cursor(1),
                                "endCursor": offset_to_cursor(2),
                            },
                            "edges": [
                                {
                                    "cursor": offset_to_cursor(1),
                                    "node": {"name": "Assignee 2"},
                                },
                                {
                                    "cursor": offset_to_cursor(2),
                                    "node": {"name": "Assignee 3"},
                                },
                            ],
                        },
                    },
                },
                {
                    "node": {
                        "name": "Task 2",
                        "assignees": {
                            "totalCount": 2,
                            "pageInfo": {
                                "hasNextPage": False,
                                "hasPreviousPage": True,
                                "startCursor": offset_to_cursor(2),
                                "endCursor": offset_to_cursor(3),
                            },
                            "edges": [
                                {
                                    "cursor": offset_to_cursor(2),
                                    "node": {"name": "Assignee 3"},
                                },
                                {
                                    "cursor": offset_to_cursor(3),
                                    "node": {"name": "Assignee 4"},
                                },
                            ],
                        },
                    },
                },
                {
                    "node": {
                        "name": "Task 3",
                        "assignees": {
                            "totalCount": 1,
                            "pageInfo": {
                                "hasNextPage": False,
                                "hasPreviousPage": True,
                                "startCursor": offset_to_cursor(4),
                                "endCursor": offset_to_cursor(4),
                            },
                            "edges": [
                                {
                                    "cursor": offset_to_cursor(4),
                                    "node": {"name": "Assignee 5"},
                                },
                            ],
                        },
                    },
                },
            ],
        },
    }

    response.assert_query_count(2)


@pytest.mark.django_db
def test_optimizer__relay__nested_connection__joins(graphql) -> None:
    TeamType = query_type(Team, fields=["name"])

    PersonType = query_type(Person, node=True, fields=["name"], teams=TeamType)

    TaskType = query_type(Task, node=True, fields=["name"], assignees=Connection(PersonType))

    class Query(graphene.ObjectType):
        tasks = DjangoConnectionField(TaskType)

    graphql.schema = graphene.Schema(query=Query)

    team_1 = TeamFactory.create(name="Team 1")
    team_2 = TeamFactory.create(name="Team 2")

    person_1 = PersonFactory.create(name="Assignee 1", teams=[team_1])
    person_2 = PersonFactory.create(name="Assignee 2", teams=[team_1])
    person_3 = PersonFactory.create(name="Assignee 3", teams=[team_2])
    person_4 = PersonFactory.create(name="Assignee 4", teams=[team_2])
    person_5 = PersonFactory.create(name="Assignee 5", teams=[team_1, team_2])

    TaskFactory.create(name="Task 1", assignees=[person_1, person_2, person_3])
    TaskFactory.create(name="Task 2", assignees=[person_3, person_4])
    TaskFactory.create(name="Task 3", assignees=[person_5])

    query = """
        query {
          tasks {
            edges {
              node {
                name
                assignees {
                  edges {
                    node {
                      name
                      teams {
                        name
                      }
                    }
                  }
                }
              }
            }
          }
        }
    """

    response = graphql(query, count_queries=True)

    assert response.has_errors is False, response.errors
    assert response.data == {
        "tasks": {
            "edges": [
                {
                    "node": {
                        "name": "Task 1",
                        "assignees": {
                            "edges": [
                                {
                                    "node": {
                                        "name": "Assignee 1",
                                        "teams": [{"name": "Team 1"}],
                                    },
                                },
                                {
                                    "node": {
                                        "name": "Assignee 2",
                                        "teams": [{"name": "Team 1"}],
                                    },
                                },
                                {
                                    "node": {
                                        "name": "Assignee 3",
                                        "teams": [{"name": "Team 2"}],
                                    },
                                },
                            ],
                        },
                    },
                },
                {
                    "node": {
                        "name": "Task 2",
                        "assignees": {
                            "edges": [
                                {
                                    "node": {
                                        "name": "Assignee 3",
                                        "teams": [{"name": "Team 2"}],
                                    },
                                },
                                {
                                    "node": {
                                        "name": "Assignee 4",
                                        "teams": [{"name": "Team 2"}],
                                    },
                                },
                            ],
                        },
                    },
                },
                {
                    "node": {
                        "name": "Task 3",
                        "assignees": {
                            "edges": [
                                {
                                    "node": {
                                        "name": "Assignee 5",
                                        "teams": [{"name": "Team 1"}, {"name": "Team 2"}],
                                    },
                                },
                            ],
                        },
                    },
                },
            ],
        },
    }

    response.assert_query_count(4)  # +1: top-level COUNT query


@pytest.mark.django_db
def test_optimizer__relay__nested_connection__joins__connection_info(graphql) -> None:
    TeamType = query_type(Team, fields=["name"])

    PersonType = query_type(Person, node=True, fields=["name"], teams=TeamType)

    TaskType = query_type(Task, node=True, fields=["name"], assignees=Connection(PersonType))

    class Query(graphene.ObjectType):
        tasks = DjangoConnectionField(TaskType)

    graphql.schema = graphene.Schema(query=Query)

    team_1 = TeamFactory.create(name="Team 1")
    team_2 = TeamFactory.create(name="Team 2")

    person_1 = PersonFactory.create(name="Assignee 1", teams=[team_1])
    person_2 = PersonFactory.create(name="Assignee 2", teams=[team_1])
    person_3 = PersonFactory.create(name="Assignee 3", teams=[team_2])
    person_4 = PersonFactory.create(name="Assignee 4", teams=[team_2])
    person_5 = PersonFactory.create(name="Assignee 5", teams=[team_1, team_2])

    TaskFactory.create(name="Task 1", assignees=[person_1, person_2, person_3])
    TaskFactory.create(name="Task 2", assignees=[person_3, person_4])
    TaskFactory.create(name="Task 3", assignees=[person_5])

    query = """
        query {
          tasks {
            edges {
              node {
                name
                assignees {
                  totalCount
                  pageInfo {
                    hasNextPage
                    hasPreviousPage
                    startCursor
                    endCursor
                  }
                  edges {
                    cursor
                    node {
                      name
                      teams {
                        name
                      }
                    }
                  }
                }
              }
            }
          }
        }
    """

    response = graphql(query, count_queries=True)

    assert response.has_errors is False, response.errors
    assert response.data == {
        "tasks": {
            "edges": [
                {
                    "node": {
                        "name": "Task 1",
                        "assignees": {
                            "totalCount": 3,
                            "pageInfo": {
                                "hasNextPage": False,
                                "hasPreviousPage": False,
                                "startCursor": offset_to_cursor(0),
                                "endCursor": offset_to_cursor(2),
                            },
                            "edges": [
                                {
                                    "cursor": offset_to_cursor(0),
                                    "node": {
                                        "name": "Assignee 1",
                                        "teams": [{"name": "Team 1"}],
                                    },
                                },
                                {
                                    "cursor": offset_to_cursor(1),
                                    "node": {
                                        "name": "Assignee 2",
                                        "teams": [{"name": "Team 1"}],
                                    },
                                },
                                {
                                    "cursor": offset_to_cursor(2),
                                    "node": {
                                        "name": "Assignee 3",
                                        "teams": [{"name": "Team 2"}],
                                    },
                                },
                            ],
                        },
                    },
                },
                {
                    "node": {
                        "name": "Task 2",
                        "assignees": {
                            "totalCount": 2,
                            "pageInfo": {
                                "hasNextPage": False,
                                "hasPreviousPage": False,
                                "startCursor": offset_to_cursor(2),
                                "endCursor": offset_to_cursor(3),
                            },
                            "edges": [
                                {
                                    "cursor": offset_to_cursor(2),
                                    "node": {
                                        "name": "Assignee 3",
                                        "teams": [{"name": "Team 2"}],
                                    },
                                },
                                {
                                    "cursor": offset_to_cursor(3),
                                    "node": {
                                        "name": "Assignee 4",
                                        "teams": [{"name": "Team 2"}],
                                    },
                                },
                            ],
                        },
                    },
                },
                {
                    "node": {
                        "name": "Task 3",
                        "assignees": {
                            "totalCount": 1,
                            "pageInfo": {
                                "hasNextPage": False,
                                "hasPreviousPage": False,
                                "startCursor": offset_to_cursor(4),
                                "endCursor": offset_to_cursor(4),
                            },
                            "edges": [
                                {
                                    "cursor": offset_to_cursor(4),
                                    "node": {
                                        "name": "Assignee 5",
                                        "teams": [{"name": "Team 1"}, {"name": "Team 2"}],
                                    },
                                },
                            ],
                        },
                    },
                },
            ],
        },
    }

    response.assert_query_count(3)


@pytest.mark.django_db
def test_optimizer__relay__nested_connection__total_count_in_fragment(graphql) -> None:
    PersonType = query_type(Person, node=True, fields=["name"])

    TaskType = query_type(Task, node=True, fields=["name"], assignees=Connection(PersonType))

    class Query(graphene.ObjectType):
        tasks = DjangoConnectionField(TaskType)

    graphql.schema = graphene.Schema(query=Query)

    person_1 = PersonFactory.create(name="Assignee 1")
    person_2 = PersonFactory.create(name="Assignee 2")
    person_3 = PersonFactory.create(name="Assignee 3")
    person_4 = PersonFactory.create(name="Assignee 4")
    person_5 = PersonFactory.create(name="Assignee 5")

    TaskFactory.create(name="Task 1", assignees=[person_1, person_2, person_3])
    TaskFactory.create(name="Task 2", assignees=[person_3, person_4])
    TaskFactory.create(name="Task 3", assignees=[person_5])

    query = """
        fragment Assignees on PersonTypeConnection {
          totalCount
          edges {
            node {
              name
            }
          }
        }

        query {
          tasks {
            edges {
              node {
                name
                assignees {
                  ...Assignees
                }
              }
            }
          }
        }
    """

    response = graphql(query, count_queries=True)

    assert response.has_errors is False, response.errors
    assert response.data == {
        "tasks": {
            "edges": [
                {
                    "node": {
                        "name": "Task 1",
                        "assignees": {
                            "totalCount": 3,
                            "edges": [
                                {"node": {"name": "Assignee 1"}},
                                {"node": {"name": "Assignee 2"}},
                                {"node": {"name": "Assignee 3"}},
                            ],
                        },
                    },
                },
                {
                    "node": {
                        "name": "Task 2",
                        "assignees": {
                            "totalCount": 2,
                            "edges": [
                                {"node": {"name": "Assignee 3"}},
                                {"node": {"name": "Assignee 4"}},
                            ],
                        },
                    },
                },
                {
                    "node": {
                        "name": "Task 3",
                        "assignees": {
                            "totalCount": 1,
                            "edges": [
                                {"node": {"name": "Assignee 5"}},
                            ],
                        },
                    },
                },
            ],
        },
    }

    response.assert_query_count(3)  # +1: top-level COUNT query


@pytest.mark.django_db
def test_optimizer__relay__nested_connection__one_to_many(graphql) -> None:
    TaskStepType = query_type(TaskStep, node=True, fields=["name"])

    TaskType = query_type(Task, node=True, fields=["name"], steps=Connection(TaskStepType))

    class Query(graphene.ObjectType):
        tasks = DjangoConnectionField(TaskType)

    graphql.schema = graphene.Schema(query=Query)

    task_1 = TaskFactory.create(name="Task 1")
    task_2 = TaskFactory.create(name="Task 2")
    task_3 = TaskFactory.create(name="Task 3")

    TaskStepFactory.create(name="Task Step 1", task=task_1)
    TaskStepFactory.create(name="Task Step 2", task=task_1)
    TaskStepFactory.create(name="Task Step 3", task=task_2)
    TaskStepFactory.create(name="Task Step 4", task=task_2)
    TaskStepFactory.create(name="Task Step 5", task=task_3)

    query = """
        query {
          tasks {
            edges {
              node {
                name
                steps {
                  edges {
                    node {
                      name
                    }
                  }
                }
              }
            }
          }
        }
    """

    response = graphql(query, count_queries=True)

    assert response.has_errors is False, response.errors
    assert response.data == {
        "tasks": {
            "edges": [
                {
                    "node": {
                        "name": "Task 1",
                        "steps": {
                            "edges": [
                                {"node": {"name": "Task Step 1"}},
                                {"node": {"name": "Task Step 2"}},
                            ],
                        },
                    },
                },
                {
                    "node": {
                        "name": "Task 2",
                        "steps": {
                            "edges": [
                                {"node": {"name": "Task Step 3"}},
                                {"node": {"name": "Task Step 4"}},
                            ],
                        },
                    },
                },
                {
                    "node": {
                        "name": "Task 3",
                        "steps": {
                            "edges": [
                                {"node": {"name": "Task Step 5"}},
                            ],
                        },
                    },
                },
            ],
        },
    }

    response.assert_query_count(3)  # +1: top-level COUNT query


@pytest.mark.django_db
def test_optimizer__relay__nested_connection__one_to_many__total_count(graphql) -> None:
    TaskStepType = query_type(TaskStep, node=True, fields=["name"])

    TaskType = query_type(Task, node=True, fields=["name"], steps=Connection(TaskStepType))

    class Query(graphene.ObjectType):
        tasks = DjangoConnectionField(TaskType)

    graphql.schema = graphene.Schema(query=Query)

    task_1 = TaskFactory.create(name="Task 1")
    task_2 = TaskFactory.create(name="Task 2")
    task_3 = TaskFactory.create(name="Task 3")

    TaskStepFactory.create(name="Task Step 1", task=task_1)
    TaskStepFactory.create(name="Task Step 2", task=task_1)
    TaskStepFactory.create(name="Task Step 3", task=task_2)
    TaskStepFactory.create(name="Task Step 4", task=task_2)
    TaskStepFactory.create(name="Task Step 5", task=task_3)

    query = """
        query {
          tasks {
            edges {
              node {
                name
                steps {
                  totalCount
                  edges {
                    node {
                      name
                    }
                  }
                }
              }
            }
          }
        }
    """

    response = graphql(query, count_queries=True)

    assert response.has_errors is False, response.errors
    assert response.data == {
        "tasks": {
            "edges": [
                {
                    "node": {
                        "name": "Task 1",
                        "steps": {
                            "totalCount": 2,
                            "edges": [
                                {"node": {"name": "Task Step 1"}},
                                {"node": {"name": "Task Step 2"}},
                            ],
                        },
                    },
                },
                {
                    "node": {
                        "name": "Task 2",
                        "steps": {
                            "totalCount": 2,
                            "edges": [
                                {"node": {"name": "Task Step 3"}},
                                {"node": {"name": "Task Step 4"}},
                            ],
                        },
                    },
                },
                {
                    "node": {
                        "name": "Task 3",
                        "steps": {
                            "totalCount": 1,
                            "edges": [
                                {"node": {"name": "Task Step 5"}},
                            ],
                        },
                    },
                },
            ],
        },
    }

    response.assert_query_count(3)  # +1: top-level COUNT query


@pytest.mark.django_db
def test_optimizer__relay__nested_connection__different_ordering(graphql) -> None:
    class PersonOrderSet(OrderSet[Person]): ...

    class PersonType(QueryType[Person], auto=False, interfaces=[Node], orderset=PersonOrderSet):
        name = Field()

    TaskType = query_type(Task, node=True, fields=["name"], assignees=Connection(PersonType))

    class Query(graphene.ObjectType):
        tasks = DjangoConnectionField(TaskType)

    graphql.schema = graphene.Schema(query=Query)

    person_1 = PersonFactory.create(name="Assignee 1")
    person_2 = PersonFactory.create(name="Assignee 2")
    person_3 = PersonFactory.create(name="Assignee 3")
    person_4 = PersonFactory.create(name="Assignee 4")
    person_5 = PersonFactory.create(name="Assignee 5")

    TaskFactory.create(name="Task 1", assignees=[person_1, person_2, person_3])
    TaskFactory.create(name="Task 2", assignees=[person_3, person_4])
    TaskFactory.create(name="Task 3", assignees=[person_5])

    query = """
        query {
          tasks {
            edges {
              node {
                name
                assignees(orderBy: nameDesc, first: 2) {
                  edges {
                    node {
                      name
                    }
                  }
                }
              }
            }
          }
        }
    """

    response = graphql(query, count_queries=True)

    assert response.has_errors is False, response.errors
    assert response.data == {
        "tasks": {
            "edges": [
                {
                    "node": {
                        "name": "Task 1",
                        "assignees": {
                            "edges": [
                                {"node": {"name": "Assignee 3"}},
                                {"node": {"name": "Assignee 2"}},
                            ],
                        },
                    },
                },
                {
                    "node": {
                        "name": "Task 2",
                        "assignees": {
                            "edges": [
                                {"node": {"name": "Assignee 4"}},
                                {"node": {"name": "Assignee 3"}},
                            ],
                        },
                    },
                },
                {
                    "node": {
                        "name": "Task 3",
                        "assignees": {
                            "edges": [
                                {"node": {"name": "Assignee 5"}},
                            ],
                        },
                    },
                },
            ],
        },
    }

    response.assert_query_count(2)


@pytest.mark.django_db
def test_optimizer__relay__nested_connection__only_total_count(graphql) -> None:
    PersonType = query_type(Person, node=True, fields=["name"])

    TaskType = query_type(Task, node=True, fields=["name"], assignees=Connection(PersonType))

    class Query(graphene.ObjectType):
        tasks = DjangoConnectionField(TaskType)

    graphql.schema = graphene.Schema(query=Query)

    person_1 = PersonFactory.create(name="Assignee 1")
    person_2 = PersonFactory.create(name="Assignee 2")
    person_3 = PersonFactory.create(name="Assignee 3")
    person_4 = PersonFactory.create(name="Assignee 4")
    person_5 = PersonFactory.create(name="Assignee 5")

    TaskFactory.create(name="Task 1", assignees=[person_1, person_2, person_3])
    TaskFactory.create(name="Task 2", assignees=[person_3, person_4])
    TaskFactory.create(name="Task 3", assignees=[person_5])

    query = """
        query {
          tasks {
            edges {
              node {
                name
                assignees {
                  totalCount
                }
              }
            }
          }
        }
    """

    response = graphql(query, count_queries=True)

    assert response.has_errors is False, response.errors
    assert response.data == {
        "tasks": {
            "edges": [
                {
                    "node": {
                        "name": "Task 1",
                        "assignees": {
                            "totalCount": 3,
                        },
                    },
                },
                {
                    "node": {
                        "name": "Task 2",
                        "assignees": {
                            "totalCount": 2,
                        },
                    },
                },
                {
                    "node": {
                        "name": "Task 3",
                        "assignees": {
                            "totalCount": 1,
                        },
                    },
                },
            ],
        },
    }

    response.assert_query_count(3)  # +1: top-level COUNT query


@pytest.mark.django_db
def test_optimizer__relay__nested_connection__only_cursor(graphql) -> None:
    PersonType = query_type(Person, node=True, fields=["name"])

    TaskType = query_type(Task, node=True, fields=["name"], assignees=Connection(PersonType))

    class Query(graphene.ObjectType):
        tasks = DjangoConnectionField(TaskType)

    graphql.schema = graphene.Schema(query=Query)

    person_1 = PersonFactory.create(name="Assignee 1")
    person_2 = PersonFactory.create(name="Assignee 2")
    person_3 = PersonFactory.create(name="Assignee 3")
    person_4 = PersonFactory.create(name="Assignee 4")
    person_5 = PersonFactory.create(name="Assignee 5")

    TaskFactory.create(name="Task 1", assignees=[person_1, person_2, person_3])
    TaskFactory.create(name="Task 2", assignees=[person_3, person_4])
    TaskFactory.create(name="Task 3", assignees=[person_5])

    query = """
        query {
          tasks {
            edges {
              node {
                name
                assignees {
                  edges {
                    cursor
                  }
                }
              }
            }
          }
        }
    """

    response = graphql(query, count_queries=True)

    assert response.has_errors is False, response.errors
    assert response.data == {
        "tasks": {
            "edges": [
                {
                    "node": {
                        "name": "Task 1",
                        "assignees": {
                            "edges": [
                                {"cursor": offset_to_cursor(0)},
                                {"cursor": offset_to_cursor(1)},
                                {"cursor": offset_to_cursor(2)},
                            ],
                        },
                    },
                },
                {
                    "node": {
                        "name": "Task 2",
                        "assignees": {
                            "edges": [
                                {"cursor": offset_to_cursor(2)},
                                {"cursor": offset_to_cursor(3)},
                            ],
                        },
                    },
                },
                {
                    "node": {
                        "name": "Task 3",
                        "assignees": {
                            "edges": [
                                {"cursor": offset_to_cursor(4)},
                            ],
                        },
                    },
                },
            ],
        },
    }

    response.assert_query_count(2)


@pytest.mark.django_db
def test_optimizer__relay__nested_connection__multiple_connections(graphql) -> None:
    PersonType = query_type(Person, node=True, fields=["name"])

    TaskStepType = query_type(TaskStep, node=True, fields=["name"])

    TaskType = query_type(Task, node=True, fields=["name"], assignees=Connection(PersonType), steps=Connection(TaskStepType))

    class Query(graphene.ObjectType):
        tasks = DjangoConnectionField(TaskType)

    graphql.schema = graphene.Schema(query=Query)

    person_1 = PersonFactory.create(name="Assignee 1")
    person_2 = PersonFactory.create(name="Assignee 2")
    person_3 = PersonFactory.create(name="Assignee 3")
    person_4 = PersonFactory.create(name="Assignee 4")
    person_5 = PersonFactory.create(name="Assignee 5")

    task_1 = TaskFactory.create(name="Task 1", assignees=[person_1, person_2, person_3])
    task_2 = TaskFactory.create(name="Task 2", assignees=[person_3, person_4])
    task_3 = TaskFactory.create(name="Task 3", assignees=[person_5])

    TaskStepFactory.create(name="Task Step 1", task=task_1)
    TaskStepFactory.create(name="Task Step 2", task=task_1)
    TaskStepFactory.create(name="Task Step 3", task=task_2)
    TaskStepFactory.create(name="Task Step 4", task=task_2)
    TaskStepFactory.create(name="Task Step 5", task=task_3)

    query = """
        query {
          tasks {
            edges {
              node {
                name
                assignees {
                  edges {
                    node {
                      name
                    }
                  }
                }
                steps {
                  edges {
                    node {
                      name
                    }
                  }
                }
              }
            }
          }
        }
    """

    response = graphql(query, count_queries=True)

    assert response.has_errors is False, response.errors
    assert response.data == {
        "tasks": {
            "edges": [
                {
                    "node": {
                        "name": "Task 1",
                        "assignees": {
                            "edges": [
                                {"node": {"name": "Assignee 1"}},
                                {"node": {"name": "Assignee 2"}},
                                {"node": {"name": "Assignee 3"}},
                            ],
                        },
                        "steps": {
                            "edges": [
                                {"node": {"name": "Task Step 1"}},
                                {"node": {"name": "Task Step 2"}},
                            ],
                        },
                    },
                },
                {
                    "node": {
                        "name": "Task 2",
                        "assignees": {
                            "edges": [
                                {"node": {"name": "Assignee 3"}},
                                {"node": {"name": "Assignee 4"}},
                            ],
                        },
                        "steps": {
                            "edges": [
                                {"node": {"name": "Task Step 3"}},
                                {"node": {"name": "Task Step 4"}},
                            ],
                        },
                    },
                },
                {
                    "node": {
                        "name": "Task 3",
                        "assignees": {
                            "edges": [
                                {"node": {"name": "Assignee 5"}},
                            ],
                        },
                        "steps": {
                            "edges": [
                                {"node": {"name": "Task Step 5"}},
                            ],
                        },
                    },
                },
            ],
        },
    }

    response.assert_query_count(4)  # +1: top-level COUNT query


@pytest.mark.django_db
def test_optimizer__relay__nested_connection__aliased_connections(graphql) -> None:
    PersonType = query_type(Person, node=True, fields=["name"])

    TaskType = query_type(Task, node=True, fields=["name"], assignees=Connection(PersonType))

    class Query(graphene.ObjectType):
        tasks = DjangoConnectionField(TaskType)

    graphql.schema = graphene.Schema(query=Query)

    person_1 = PersonFactory.create(name="Assignee 1")
    person_2 = PersonFactory.create(name="Assignee 2")
    person_3 = PersonFactory.create(name="Assignee 3")
    person_4 = PersonFactory.create(name="Assignee 4")
    person_5 = PersonFactory.create(name="Assignee 5")

    TaskFactory.create(name="Task 1", assignees=[person_1, person_2, person_3])
    TaskFactory.create(name="Task 2", assignees=[person_3, person_4])
    TaskFactory.create(name="Task 3", assignees=[person_5])

    query = """
        query {
          tasks {
            edges {
              node {
                name
                assignees {
                  edges {
                    node {
                      name
                    }
                  }
                }
                persons: assignees(first: 1) {
                  edges {
                    node {
                      name
                    }
                  }
                }
              }
            }
          }
        }
    """

    response = graphql(query, count_queries=True)

    assert response.has_errors is False, response.errors
    assert response.data == {
        "tasks": {
            "edges": [
                {
                    "node": {
                        "name": "Task 1",
                        "assignees": {
                            "edges": [
                                {"node": {"name": "Assignee 1"}},
                                {"node": {"name": "Assignee 2"}},
                                {"node": {"name": "Assignee 3"}},
                            ],
                        },
                        "persons": {
                            "edges": [
                                {"node": {"name": "Assignee 1"}},
                            ],
                        },
                    },
                },
                {
                    "node": {
                        "name": "Task 2",
                        "assignees": {
                            "edges": [
                                {"node": {"name": "Assignee 3"}},
                                {"node": {"name": "Assignee 4"}},
                            ],
                        },
                        "persons": {
                            "edges": [
                                {"node": {"name": "Assignee 3"}},
                            ],
                        },
                    },
                },
                {
                    "node": {
                        "name": "Task 3",
                        "assignees": {
                            "edges": [
                                {"node": {"name": "Assignee 5"}},
                            ],
                        },
                        "persons": {
                            "edges": [
                                {"node": {"name": "Assignee 5"}},
                            ],
                        },
                    },
                },
            ],
        },
    }

    response.assert_query_count(4)  # +1: top-level COUNT query


@pytest.mark.django_db
def test_optimizer__relay__nested_connection__generic_relation(graphql) -> None:
    CommentType = query_type(Comment, node=True, fields=["contents"])

    TaskType = query_type(Task, node=True, fields=["name"], comments=Connection(CommentType))

    class Query(graphene.ObjectType):
        tasks = DjangoConnectionField(TaskType)

    graphql.schema = graphene.Schema(query=Query)

    task_1 = TaskFactory.create(name="Task 1")
    task_2 = TaskFactory.create(name="Task 2")
    task_3 = TaskFactory.create(name="Task 3")

    CommentFactory.create(contents="Comment 1", target=task_1)
    CommentFactory.create(contents="Comment 2", target=task_1)
    CommentFactory.create(contents="Comment 3", target=task_2)
    CommentFactory.create(contents="Comment 4", target=task_2)
    CommentFactory.create(contents="Comment 5", target=task_3)

    cache_content_types()

    query = """
        query {
          tasks {
            edges {
              node {
                name
                comments {
                  edges {
                    node {
                      contents
                    }
                  }
                }
              }
            }
          }
        }
    """

    response = graphql(query, count_queries=True)

    assert response.has_errors is False, response.errors
    assert response.data == {
        "tasks": {
            "edges": [
                {
                    "node": {
                        "name": "Task 1",
                        "comments": {
                            "edges": [
                                {"node": {"contents": "Comment 1"}},
                                {"node": {"contents": "Comment 2"}},
                            ],
                        },
                    },
                },
                {
                    "node": {
                        "name": "Task 2",
                        "comments": {
                            "edges": [
                                {"node": {"contents": "Comment 3"}},
                                {"node": {"contents": "Comment 4"}},
                            ],
                        },
                    },
                },
                {
                    "node": {
                        "name": "Task 3",
                        "comments": {
                            "edges": [
                                {"node": {"contents": "Comment 5"}},
                            ],
                        },
                    },
                },
            ],
        },
    }

    response.assert_query_count(2)


@pytest.mark.django_db
def test_optimizer__relay__nested_connection__third_level_connection(graphql) -> None:
    CommentType = query_type(Comment, node=True, fields=["contents"])

    PersonType = query_type(Person, node=True, fields=["name"], comments=Connection(CommentType))

    TeamType = query_type(Team, node=True, fields=["name"], members=Connection(PersonType))

    class Query(graphene.ObjectType):
        teams = DjangoConnectionField(TeamType)

    graphql.schema = graphene.Schema(query=Query)

    task_1 = TaskFactory.create(name="Task 1", project=None)
    task_2 = TaskFactory.create(name="Task 2", project=None)
    task_3 = TaskFactory.create(name="Task 3", project=None)

    person_1 = PersonFactory.create(name="Assignee 1")
    person_2 = PersonFactory.create(name="Assignee 2")
    person_3 = PersonFactory.create(name="Assignee 3")
    person_4 = PersonFactory.create(name="Assignee 4")
    person_5 = PersonFactory.create(name="Assignee 5")

    CommentFactory.create(contents="Comment 1", commenter=person_1, target=task_1)
    CommentFactory.create(contents="Comment 2", commenter=person_2, target=task_1)
    CommentFactory.create(contents="Comment 3", commenter=person_2, target=task_2)
    CommentFactory.create(contents="Comment 4", commenter=person_3, target=task_2)
    CommentFactory.create(contents="Comment 5", commenter=person_3, target=task_3)
    CommentFactory.create(contents="Comment 6", commenter=person_5, target=task_3)

    TeamFactory.create(name="Team 1", members=[person_1, person_2, person_3])
    TeamFactory.create(name="Team 2", members=[person_3, person_4])
    TeamFactory.create(name="Team 3", members=[person_5])

    query = """
        query {
          teams {
            edges {
              node {
                name
                members {
                  edges {
                    node {
                      name
                      comments {
                        edges {
                          node {
                            contents
                          }
                        }
                      }
                    }
                  }
                }
              }
            }
          }
        }
    """

    response = graphql(query, count_queries=True)

    assert response.has_errors is False, response.errors
    assert response.data == {
        "teams": {
            "edges": [
                {
                    "node": {
                        "name": "Team 1",
                        "members": {
                            "edges": [
                                {
                                    "node": {
                                        "name": "Assignee 1",
                                        "comments": {
                                            "edges": [
                                                {"node": {"contents": "Comment 1"}},
                                            ],
                                        },
                                    },
                                },
                                {
                                    "node": {
                                        "name": "Assignee 2",
                                        "comments": {
                                            "edges": [
                                                {"node": {"contents": "Comment 2"}},
                                                {"node": {"contents": "Comment 3"}},
                                            ],
                                        },
                                    },
                                },
                                {
                                    "node": {
                                        "name": "Assignee 3",
                                        "comments": {
                                            "edges": [
                                                {"node": {"contents": "Comment 4"}},
                                                {"node": {"contents": "Comment 5"}},
                                            ],
                                        },
                                    },
                                },
                            ],
                        },
                    },
                },
                {
                    "node": {
                        "name": "Team 2",
                        "members": {
                            "edges": [
                                {
                                    "node": {
                                        "name": "Assignee 3",
                                        "comments": {
                                            "edges": [
                                                {"node": {"contents": "Comment 4"}},
                                                {"node": {"contents": "Comment 5"}},
                                            ],
                                        },
                                    },
                                },
                                {
                                    "node": {
                                        "name": "Assignee 4",
                                        "comments": {
                                            "edges": [],
                                        },
                                    },
                                },
                            ],
                        },
                    },
                },
                {
                    "node": {
                        "name": "Team 3",
                        "members": {
                            "edges": [
                                {
                                    "node": {
                                        "name": "Assignee 5",
                                        "comments": {
                                            "edges": [
                                                {"node": {"contents": "Comment 6"}},
                                            ],
                                        },
                                    },
                                },
                            ],
                        },
                    },
                },
            ],
        },
    }

    response.assert_query_count(4)  # +1: top-level COUNT query


# Offset pagination


@pytest.mark.django_db
def test_optimizer__offset_pagination(graphql) -> None:
    TaskType = query_type(Task, fields=["name"])

    class Query(graphene.ObjectType):
        tasks = Entrypoint(OffsetPagination(TaskType))

    graphql.schema = graphene.Schema(query=Query)

    TaskFactory.create(name="Task 1")
    TaskFactory.create(name="Task 2")
    TaskFactory.create(name="Task 3")

    query = """
        query ($offset: Int!) {
          tasks(offset: $offset) {
            name
          }
        }
    """

    response = graphql(query, variables={"offset": 1}, count_queries=True)

    assert response.has_errors is False, response.errors
    assert response.data == {
        "tasks": [
            {"name": "Task 2"},
            {"name": "Task 3"},
        ],
    }

    response.assert_query_count(1)


@pytest.mark.django_db
def test_optimizer__offset_pagination__nested(graphql) -> None:
    PersonType = query_type(Person, fields=["name"])

    TaskType = query_type(Task, fields=["name"], assignees=OffsetPagination(PersonType))

    class Query(graphene.ObjectType):
        tasks = Entrypoint(OffsetPagination(TaskType))

    graphql.schema = graphene.Schema(query=Query)

    person_1 = PersonFactory.create(name="Assignee 1")
    person_2 = PersonFactory.create(name="Assignee 2")
    person_3 = PersonFactory.create(name="Assignee 3")
    person_4 = PersonFactory.create(name="Assignee 4")
    person_5 = PersonFactory.create(name="Assignee 5")

    TaskFactory.create(name="Task 1", assignees=[person_1, person_2, person_3])
    TaskFactory.create(name="Task 2", assignees=[person_3, person_4])
    TaskFactory.create(name="Task 3", assignees=[person_5])

    query = """
        query {
          tasks {
            name
            assignees(offset: 1) {
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
                "name": "Task 1",
                "assignees": [
                    {"name": "Assignee 2"},
                    {"name": "Assignee 3"},
                ],
            },
            {
                "name": "Task 2",
                "assignees": [
                    {"name": "Assignee 4"},
                ],
            },
            {
                "name": "Task 3",
                "assignees": [],
            },
        ]
    }

    response.assert_query_count(2)
