from __future__ import annotations

from typing import TYPE_CHECKING

import graphene
import graphene_django.filter
from django.db import models
from graphene.utils.str_converters import to_snake_case
from graphene_django import DjangoListField
from graphene_django.converter import convert_django_field, get_django_field_description
from graphene_django.registry import Registry  # noqa: TCH002

from .cache import store_in_query_cache
from .optimizer import QueryOptimizer
from .utils import get_field_type, get_selections

if TYPE_CHECKING:
    from django.db.models.manager import Manager
    from graphene.relay.connection import Connection
    from graphql_relay import EdgeType
    from graphql_relay.connection.connection import ConnectionType

    from .types import DjangoObjectType
    from .typing import Any, Callable, GQLInfo, Optional, TypeAlias, TypeVar

    TModel = TypeVar("TModel", bound=models.Model)

    Args: TypeAlias = tuple[
        Callable[..., Optional[Manager[TModel]]],  # resolver
        Connection,  # connection
        Manager[TModel],  # default_manager
        Callable[..., models.QuerySet[TModel]],  # queryset_resolver
        int,  # max_limit
        bool,  # enforce_first_or_last
        Optional[models.Model],  # enforce_first_or_last
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


@convert_django_field.register(models.OneToOneRel)
def convert_reverse_to_one_field_to_django_model(
    field,  # noqa: ANN001
    registry: Registry | None = None,
) -> graphene.Dynamic:
    def dynamic_type() -> graphene.Field | None:
        _type: DjangoObjectType | None = registry.get_type_for_model(field.related_model)
        if _type is None:  # pragma: no cover
            return None

        class CustomField(graphene.Field):
            def wrap_resolve(self, parent_resolver: Any) -> Any:
                def custom_resolver(root: Any, info: GQLInfo) -> models.Model | None:
                    field_name = to_snake_case(info.field_name)
                    # Reverse object should be optimized to the root model.
                    reverse_object: models.Model | None = getattr(root, field_name, None)
                    if reverse_object is None:  # pragma: no cover
                        return None

                    return _type.get_node(info, reverse_object.pk)

                return custom_resolver

        return CustomField(_type, description=get_django_field_description(field.field), required=not field.null)

    return graphene.Dynamic(dynamic_type)


@convert_django_field.register(models.OneToOneField)
@convert_django_field.register(models.ForeignKey)
def convert_forward_to_one_field_to_django_model(
    field,  # noqa: ANN001
    registry: Registry | None = None,
) -> graphene.Dynamic:
    def dynamic_type() -> graphene.Field | None:
        _type: DjangoObjectType | None = registry.get_type_for_model(field.related_model)
        if _type is None:  # pragma: no cover
            return None

        class CustomField(graphene.Field):
            def wrap_resolve(self, parent_resolver: Any) -> Any:
                def custom_resolver(root: Any, info: GQLInfo) -> models.Model | None:
                    field_name = to_snake_case(info.field_name)
                    db_field_key: str = root.__class__._meta.get_field(field_name).attname
                    object_pk = getattr(root, db_field_key, None)
                    if object_pk is None:  # pragma: no cover
                        return None

                    return _type.get_node(info, object_pk)

                return custom_resolver

        return CustomField(_type, description=get_django_field_description(field), required=not field.null)

    return graphene.Dynamic(dynamic_type)


@convert_django_field.register(models.ManyToManyField)
@convert_django_field.register(models.ManyToManyRel)
@convert_django_field.register(models.ManyToOneRel)
def convert_to_many_field_to_list_or_connection(
    field,  # noqa: ANN001
    registry: Registry | None = None,
) -> graphene.Dynamic:
    def dynamic_type() -> graphene_django.fields.DjangoConnectionField | DjangoListField | None:
        _type: DjangoObjectType | None = registry.get_type_for_model(field.related_model)
        if _type is None:  # pragma: no cover
            return None

        description = get_django_field_description(field if isinstance(field, models.ManyToManyField) else field.field)

        if _type._meta.connection:
            if _type._meta.filter_fields or _type._meta.filterset_class:  # pragma: no cover
                from .filter import DjangoFilterConnectionField

                return DjangoFilterConnectionField(_type, required=True, description=description)
            return DjangoConnectionField(_type, required=True, description=description)
        return DjangoListField(_type, required=True, description=description)

    return graphene.Dynamic(dynamic_type)
