import graphene_django.filter
from django.db.models import Model, QuerySet
from django.db.models.manager import Manager
from graphene.relay.connection import Connection
from graphql_relay import EdgeType
from graphql_relay.connection.connection import ConnectionType

from .cache import store_in_query_cache
from .optimizer import QueryOptimizer
from .typing import Any, Callable, GQLInfo, Optional, TypeAlias, TypeVar
from .utils import get_field_type, get_selections

TModel = TypeVar("TModel", bound=Model)

__all__ = [
    "ConnectionFieldCachingMixin",
    "DjangoConnectionField",
]

Args: TypeAlias = tuple[
    Callable[..., Optional[Manager[TModel]]],  # resolver
    Connection,  # connection
    Manager[TModel],  # default_manager
    Callable[..., QuerySet[TModel]],  # queryset_resolver
    int,  # max_limit
    bool,  # enforce_first_or_last
    Optional[Model],  # enforce_first_or_last
    GQLInfo,  # info
]


class ConnectionFieldCachingMixin:
    @classmethod
    def connection_resolver(cls, *args: Any, **kwargs: Any) -> ConnectionType:
        args: Args  # type: ignore[no-redef]
        connection_field: graphene_django.fields.DjangoConnectionField = super()  # type: ignore[override]
        connection_type: ConnectionType = connection_field.connection_resolver(*args, **kwargs)
        cache_edges(connection_type.edges, args[2].model, args[7])
        return connection_type


class DjangoConnectionField(
    ConnectionFieldCachingMixin,
    graphene_django.fields.DjangoConnectionField,
):
    pass


def cache_edges(edges: list[EdgeType], model: type[Model], info: GQLInfo) -> None:
    if not edges:
        return

    field_type = get_field_type(info)
    selections = get_selections(info)
    optimizer = QueryOptimizer(info)
    store = optimizer.optimize_selections(field_type, selections, model)
    store_in_query_cache(
        key=info.operation,
        items=(edge.node for edge in edges),
        schema=info.schema,
        store=store,
    )
