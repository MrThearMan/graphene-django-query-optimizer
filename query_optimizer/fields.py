import graphene_django.filter
from django.db.models import Model, QuerySet
from django.db.models.manager import Manager
from graphene.relay.connection import Connection
from graphql_relay.connection.connection import ConnectionType

from .cache import store_in_query_cache
from .optimizer import QueryOptimizer
from .typing import Any, Callable, GQLInfo, TypeVar, Union
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
        resolver: Callable[..., Union[Manager[TModel], None]],
        connection: Connection,
        default_manager: Manager[TModel],
        queryset_resolver: Callable[..., QuerySet[TModel]],
        max_limit: int,
        enforce_first_or_last: bool,  # noqa: FBT001
        root: Union[Model, None],
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
        if not connection_type.edges:
            return connection_type

        field_type = get_field_type(info)
        selections = get_selections(info)
        optimizer = QueryOptimizer(info)
        store = optimizer.optimize_selections(field_type, selections)
        store_in_query_cache(
            key=info.operation,
            items=(edge.node for edge in connection_type.edges),
            schema=info.schema,
            store=store,
        )

        return connection_type


class DjangoConnectionField(
    ConnectionFieldCachingMixin,
    graphene_django.fields.DjangoConnectionField,
):
    pass
