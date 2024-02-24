# ruff: noqa: UP006
from __future__ import annotations

from functools import cached_property
from typing import TYPE_CHECKING, Type

import graphene
from django.core.exceptions import ValidationError
from graphene.relay import ConnectionField
from graphene.relay.connection import connection_adapter, page_info_adapter
from graphene.types.argument import to_arguments
from graphene.types.utils import get_type
from graphene_django.settings import graphene_settings
from graphene_django.utils.utils import maybe_queryset
from graphql_relay.connection.array_connection import offset_to_cursor

from .cache import store_in_query_cache
from .optimizer import QueryOptimizer
from .utils import calculate_queryset_slice, get_field_type, get_selections
from .validators import validate_pagination_args

if TYPE_CHECKING:
    from django.db import models
    from django.db.models.manager import Manager
    from django_filters import FilterSet
    from graphene.relay.connection import Connection
    from graphql_relay import EdgeType
    from graphql_relay.connection.connection import ConnectionType

    from .types import DjangoObjectType
    from .typing import Any, ConnectionResolver, GQLInfo, QuerySetResolver, TypeVar

    TModel = TypeVar("TModel", bound=models.Model)


__all__ = [
    "DjangoConnectionField",
]


# Reimplemented relay ConnectionField for better control for optimizer.
class DjangoConnectionField(ConnectionField):
    """Connection field for Django models that works for both nodes and regular object types."""

    def __init__(self, type_: Type[DjangoObjectType], **kwargs: Any) -> None:
        """
        Initialize a connection field for the given type.

        :param type_: DjangoObjectType the connection is for.
        :param kwargs: Extra arguments passed to `graphene.types.field.Field`.
        """
        # Maximum number of items that can be requested in a single query for this connection.
        # Set to None to disable the limit.
        self.max_limit: int | None = kwargs.get("max_limit", graphene_settings.RELAY_CONNECTION_MAX_LIMIT)

        self._base_args: dict[str, Any] | None = None
        self._filterset_class: Type[FilterSet] | None = None
        self._filtering_args: dict[str, graphene.Argument] | None = None

        # Default inputs for a connection field
        kwargs.setdefault("first", graphene.Int())
        kwargs.setdefault("last", graphene.Int())
        kwargs.setdefault("offset", graphene.Int())
        kwargs.setdefault("after", graphene.String())
        kwargs.setdefault("before", graphene.String())

        super().__init__(type_, **kwargs)

    def wrap_resolve(self, parent_resolver: QuerySetResolver) -> ConnectionResolver:
        self.resolver = parent_resolver
        return self.resolve

    def resolve(self, root: Any, info: GQLInfo, **kwargs: Any) -> ConnectionType:
        pagination_args = validate_pagination_args(
            first=kwargs.get("first"),
            last=kwargs.get("last"),
            offset=kwargs.get("offset"),
            after=kwargs.get("after"),
            before=kwargs.get("before"),
            max_limit=self.max_limit,
        )

        # Call the ObjectType's "resolve_{field_name}" method if it exists.
        # Otherwise, call the default resolver (usually `dict_or_attr_resolver`).
        result = self.resolver(root, info, **kwargs)

        queryset = self.to_queryset(result)
        # TODO: Should do filtering for nested fields as well.
        queryset = self.filter_queryset(queryset, info, kwargs)
        optimized_queryset = self.node_type.get_queryset(queryset, info)

        # Queryset optimization contains filtering, so we count after optimization.
        pagination_args["size"] = count = optimized_queryset.count()

        # Slice a queryset using the calculated pagination arguments.
        cut = calculate_queryset_slice(**pagination_args)
        iterable = optimized_queryset[cut]

        # Store data in cache
        field_type = get_field_type(info)
        selections = get_selections(info)
        optimizer = QueryOptimizer(info)
        store = optimizer.optimize_selections(field_type, selections, model=self.model)
        store_in_query_cache(key=info.operation, items=iterable, schema=info.schema, store=store)

        # Create a connection from the sliced queryset.
        edges: list[EdgeType] = [
            # Connection type does contain an Edge, it's just added dynamically.
            self.connection_type.Edge(node=value, cursor=offset_to_cursor(cut.start + index))
            for index, value in enumerate(iterable)
        ]
        connection = connection_adapter(
            cls=self.connection_type,
            edges=edges,
            pageInfo=page_info_adapter(
                startCursor=edges[0].cursor if edges else None,
                endCursor=edges[-1].cursor if edges else None,
                hasPreviousPage=cut.start > 0,
                hasNextPage=cut.stop <= count,
            ),
        )
        connection.iterable = iterable
        connection.length = count
        return connection

    def to_queryset(self, iterable: models.QuerySet | Manager | None) -> models.QuerySet:
        # Default resolver returns a Manager-instance or None.
        if iterable is None:
            iterable = self.model._default_manager
        return maybe_queryset(iterable)

    def filter_queryset(self, queryset: models.QuerySet, info: GQLInfo, input_data: dict[str, Any]) -> models.QuerySet:
        if not self.has_filters:
            return queryset

        data = self.get_filter_data(input_data)
        filterset = self.filterset_class(data=data, queryset=queryset, request=info.context)
        if filterset.is_valid():
            return filterset.qs
        raise ValidationError(filterset.form.errors.as_json())  # pragma: no cover

    def get_filter_data(self, input_data: dict[str, Any]) -> dict[str, Any]:
        from graphene_django.filter.fields import convert_enum

        data: dict[str, Any] = {}
        for key, value in input_data.items():
            if key in self.filtering_args:
                data[key] = convert_enum(value)
        return data

    @property
    def args(self) -> dict[str, graphene.Argument]:
        return to_arguments(self._base_args or {}, self.filtering_args)

    @args.setter
    def args(self, args: dict[str, Any]) -> None:
        self._base_args = args

    @cached_property
    def type(self) -> Type[Connection] | graphene.NonNull:
        from graphene_django.types import DjangoObjectType

        type_ = get_type(self._type)
        non_null = isinstance(type_, graphene.NonNull)
        if non_null:  # pragma: no cover
            type_ = type_.of_type

        if not issubclass(type_, DjangoObjectType):  # pragma: no cover
            msg = f"{self.__class__.__name__} only accepts DjangoObjectType types"
            raise TypeError(msg)

        connection_type: Type[Connection] | None = type_._meta.connection
        if connection_type is None:  # pragma: no cover
            msg = f"The type {type_.__name__} doesn't have a connection"
            raise ValueError(msg)

        if non_null:  # pragma: no cover
            return graphene.NonNull(connection_type)
        return connection_type

    @cached_property
    def connection_type(self) -> Type[Connection]:
        type_ = self.type
        if isinstance(type_, graphene.NonNull):  # pragma: no cover
            return type_.of_type
        return type_

    @cached_property
    def node_type(self) -> Type[DjangoObjectType]:
        return self.connection_type._meta.node

    @cached_property
    def model(self) -> Type[models.Model]:
        return self.node_type._meta.model

    @cached_property
    def filterset_class(self) -> Type[FilterSet] | None:
        if not self._filterset_class and self.has_filters:
            from graphene_django.filter.utils import get_filterset_class

            from .filter import FilterSet

            meta: dict[str, Any] = {
                "model": self.model,
                "fields": self.node_type._meta.filter_fields,
                "filterset_base_class": FilterSet,
            }
            self._filterset_class = get_filterset_class(self.node_type._meta.filterset_class, **meta)
        return self._filterset_class

    @cached_property
    def filtering_args(self) -> dict[Any, graphene.Argument] | None:
        if not self._filtering_args and self.has_filters:
            from graphene_django.filter.utils import get_filtering_args_from_filterset

            self._filtering_args = get_filtering_args_from_filterset(self.filterset_class, self.node_type)
        return self._filtering_args

    @cached_property
    def has_filters(self) -> bool:
        return bool(self.node_type._meta.filter_fields or self.node_type._meta.filterset_class)
