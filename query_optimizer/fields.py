from __future__ import annotations

from typing import TYPE_CHECKING

import graphene_django.filter

from .cache import store_in_query_cache
from .optimizer import QueryOptimizer
from .utils import get_field_type, get_selections

if TYPE_CHECKING:
    from django.db.models import Model, QuerySet
    from django.db.models.manager import Manager
    from graphene.relay.connection import Connection
    from graphql_relay import EdgeType
    from graphql_relay.connection.connection import ConnectionType

    from .typing import Any, Callable, GQLInfo, Optional, TypeAlias, TypeVar

    TModel = TypeVar("TModel", bound=Model)

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


__all__ = [
    "ConnectionFieldCachingMixin",
    "DjangoConnectionField",
]


class ConnectionFieldCachingMixin:
    """Mixin to add query caching to connection fields."""

    @classmethod
    def connection_resolver(cls, *args: Any, **kwargs: Any) -> ConnectionType:
        args: Args  # type: ignore[no-redef]
        connection_field: graphene_django.fields.DjangoConnectionField = super()  # type: ignore[override]
        connection_type: ConnectionType = connection_field.connection_resolver(*args, **kwargs)
        cache_edges(edges=connection_type.edges, info=args[7])
        return connection_type


class DjangoConnectionField(
    ConnectionFieldCachingMixin,
    graphene_django.fields.DjangoConnectionField,
):
    pass


def cache_edges(edges: list[EdgeType], info: GQLInfo) -> None:
    """
    Cache edges received from a connection in the query cache.

    :param edges: Edges containing the fetched models.
    :param info: The GraphQLResolveInfo object used in the optimization process.
    """
    if not edges:
        return

    field_type = get_field_type(info)
    selections = get_selections(info)
    optimizer = QueryOptimizer(info)
    store = optimizer.optimize_selections(field_type, selections, model=type(edges[0].node))
    store_in_query_cache(
        key=info.operation,
        items=(edge.node for edge in edges),
        schema=info.schema,
        store=store,
    )
