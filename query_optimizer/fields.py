import graphene_django.filter
from django.db.models import Model, QuerySet
from django.db.models.manager import Manager
from graphene.relay.connection import Connection
from graphql_relay import EdgeType
from graphql_relay.connection.connection import ConnectionType

from .cache import store_in_query_cache
from .optimizer import QueryOptimizer
from .typing import Any, Callable, GQLInfo, Optional, TypeVar
from .utils import get_field_type, get_selections

TModel = TypeVar("TModel", bound=Model)

__all__ = [
    "ConnectionFieldCachingMixin",
    "DjangoConnectionField",
]


class ConnectionFieldCachingMixin:
    @classmethod
    def connection_resolver(  # noqa: PLR0913
        cls,
        resolver: Callable[..., Optional[Manager[TModel]]],
        connection: Connection,
        default_manager: Manager[TModel],
        queryset_resolver: Callable[..., QuerySet[TModel]],
        max_limit: int,
        enforce_first_or_last: bool,  # noqa: FBT001
        root: Optional[Model],
        info: GQLInfo,
        **args: Any,
    ) -> ConnectionType:
        connection_field: graphene_django.fields.DjangoConnectionField = super()  # type: ignore[override]
        connection_type: ConnectionType = connection_field.connection_resolver(
            resolver,
            connection,
            default_manager,
            queryset_resolver,
            max_limit,
            enforce_first_or_last,
            root,
            info,
            **args,
        )
        cache_edges(connection_type.edges, default_manager.model, info)
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
