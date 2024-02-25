# ruff: noqa: UP006
from __future__ import annotations

from functools import cached_property
from typing import TYPE_CHECKING

import graphene
from django.core.exceptions import ValidationError
from graphene.relay.connection import connection_adapter, page_info_adapter
from graphene.types.argument import to_arguments
from graphene.utils.str_converters import to_snake_case
from graphene_django.settings import graphene_settings
from graphene_django.utils.utils import maybe_queryset
from graphql_relay.connection.array_connection import offset_to_cursor

from .cache import store_in_query_cache
from .optimizer import QueryOptimizer, optimize
from .settings import optimizer_settings
from .utils import calculate_queryset_slice, get_field_type, get_selections, get_underlying_type
from .validators import validate_pagination_args

if TYPE_CHECKING:
    from django.db import models
    from django.db.models.manager import Manager
    from graphene.relay.connection import Connection
    from graphene_django import DjangoObjectType
    from graphql_relay import EdgeType
    from graphql_relay.connection.connection import ConnectionType

    from .filter import FilterSet
    from .typing import (
        Any,
        ConnectionResolver,
        GQLInfo,
        ModelResolver,
        Optional,
        QuerySetResolver,
        Type,
        TypeVar,
        Union,
    )

    TModel = TypeVar("TModel", bound=models.Model)


__all__ = [
    "DjangoConnectionField",
    "DjangoListField",
    "RelatedField",
]


class RelatedField(graphene.Field):
    """Field for `to-one` related models with automatic node resolution."""

    def __init__(self, type_: Union[Type[DjangoObjectType], str], *, reverse: bool = False, **kwargs: Any) -> None:
        """
        Initialize a related field for the given type.

        :param type_: Object type or dot import path to the object type.
        :param reverse: Is the relation direction forward or reverse?
        :param kwargs: Extra arguments passed to `graphene.types.field.Field`.
        """
        self.reverse = reverse
        super().__init__(type_, **kwargs)

    def wrap_resolve(self, parent_resolver: ModelResolver) -> ModelResolver:
        if self.reverse:
            return self.reverse_resolver
        return self.forward_resolver

    def forward_resolver(self, root: models.Model, info: GQLInfo) -> Optional[models.Model]:
        field_name = to_snake_case(info.field_name)
        db_field_key: str = root.__class__._meta.get_field(field_name).attname
        object_pk = getattr(root, db_field_key, None)
        if object_pk is None:  # pragma: no cover
            return None
        return self.underlying_type.get_node(info, object_pk)

    def reverse_resolver(self, root: models.Model, info: GQLInfo) -> Optional[models.Model]:
        field_name = to_snake_case(info.field_name)
        # Reverse object should be optimized to the root model.
        reverse_object: Optional[models.Model] = getattr(root, field_name, None)
        if reverse_object is None:  # pragma: no cover
            return None
        return self.underlying_type.get_node(info, reverse_object.pk)

    @cached_property
    def underlying_type(self) -> Type[DjangoObjectType]:
        return get_underlying_type(self.type)


class FilteringMixin:
    # Subclasses should implement the following properties:
    model: type[models.Model]
    underlying_type: type[DjangoObjectType]

    @property
    def args(self) -> dict[str, graphene.Argument]:
        return to_arguments(getattr(self, "_base_args", None) or {}, self.filtering_args)

    @args.setter
    def args(self, args: dict[str, Any]) -> None:
        # noinspection PyAttributeOutsideInit
        self._base_args = args

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

    @cached_property
    def filterset_class(self) -> Optional[type[FilterSet]]:
        if not self.has_filters:
            return None

        from .filter import get_filterset_for_object_type

        return get_filterset_for_object_type(self.underlying_type)

    @cached_property
    def filtering_args(self) -> Optional[dict[str, graphene.Argument]]:
        if not self.has_filters:
            return None

        from graphene_django.filter.utils import get_filtering_args_from_filterset

        return get_filtering_args_from_filterset(self.filterset_class, self.underlying_type)

    @cached_property
    def has_filters(self) -> bool:
        return bool(self.underlying_type._meta.filter_fields or self.underlying_type._meta.filterset_class)


class DjangoListField(FilteringMixin, graphene.Field):
    """Django list field that also supports filtering."""

    def __init__(self, type_: Union[Type[DjangoObjectType], str], **kwargs: Any) -> None:
        """
        Initialize a list field for the given type.

        :param type_: Object type or dot import path to the object type.
        :param kwargs:  Extra arguments passed to `graphene.types.field.Field`.
        """
        if isinstance(type_, graphene.NonNull):  # pragma: no cover
            type_ = type_.of_type
        super().__init__(graphene.List(graphene.NonNull(type_)), **kwargs)

    def wrap_resolve(self, parent_resolver: QuerySetResolver) -> QuerySetResolver:
        self.resolver = parent_resolver
        return self.list_resolver

    def list_resolver(self, root: Any, info: GQLInfo, **kwargs: Any) -> models.QuerySet:
        result = self.resolver(root, info, **kwargs)
        queryset = self.to_queryset(result)
        # TODO: Should do filtering for nested fields as well.
        queryset = self.filter_queryset(queryset, info, kwargs)
        queryset = self.underlying_type.get_queryset(queryset, info)

        max_complexity = getattr(self.underlying_type._meta, "max_complexity", optimizer_settings.MAX_COMPLEXITY)
        return optimize(queryset, info, max_complexity=max_complexity)

    def to_queryset(self, iterable: Union[models.QuerySet, Manager, None]) -> models.QuerySet:
        # Default resolver can return a Manager-instance or None.
        if iterable is None:
            iterable = self.model._default_manager
        return maybe_queryset(iterable)

    @cached_property
    def underlying_type(self) -> Type[DjangoObjectType]:
        return get_underlying_type(self.type)

    @cached_property
    def model(self) -> Type[models.Model]:
        return self.underlying_type._meta.model


class DjangoConnectionField(FilteringMixin, graphene.Field):
    """Connection field for Django models that works for both filtered and non-filtered Relay-nodes."""

    def __init__(self, type_: Union[Type[DjangoObjectType], str], **kwargs: Any) -> None:
        """
        Initialize a connection field for the given type.

        :param type_: DjangoObjectType the connection is for.
        :param kwargs: Extra arguments passed to `graphene.types.field.Field`.
        """
        # Maximum number of items that can be requested in a single query for this connection.
        # Set to None to disable the limit.
        self.max_limit: Optional[int] = kwargs.get("max_limit", graphene_settings.RELAY_CONNECTION_MAX_LIMIT)

        # Default inputs for a connection field
        kwargs.setdefault("first", graphene.Int())
        kwargs.setdefault("last", graphene.Int())
        kwargs.setdefault("offset", graphene.Int())
        kwargs.setdefault("after", graphene.String())
        kwargs.setdefault("before", graphene.String())

        super().__init__(type_, **kwargs)

    def wrap_resolve(self, parent_resolver: QuerySetResolver) -> ConnectionResolver:
        self.resolver = parent_resolver
        return self.connection_resolver

    def connection_resolver(self, root: Any, info: GQLInfo, **kwargs: Any) -> ConnectionType:
        pagination_args = validate_pagination_args(
            first=kwargs.pop("first", None),
            last=kwargs.pop("last", None),
            offset=kwargs.pop("offset", None),
            after=kwargs.pop("after", None),
            before=kwargs.pop("before", None),
            max_limit=self.max_limit,
        )

        # Call the ObjectType's "resolve_{field_name}" method if it exists.
        # Otherwise, call the default resolver (usually `dict_or_attr_resolver`).
        result = self.resolver(root, info, **kwargs)
        queryset = self.to_queryset(result)
        # TODO: Should do filtering for nested fields as well.
        queryset = self.filter_queryset(queryset, info, kwargs)
        queryset = self.underlying_type.get_queryset(queryset, info)

        max_complexity = getattr(self.underlying_type._meta, "max_complexity", optimizer_settings.MAX_COMPLEXITY)
        optimized_queryset = optimize(queryset, info, max_complexity=max_complexity)

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

    def to_queryset(self, iterable: Union[models.QuerySet, Manager, None]) -> models.QuerySet:
        # Default resolver can return a Manager-instance or None.
        if iterable is None:
            iterable = self.model._default_manager
        return maybe_queryset(iterable)

    @cached_property
    def type(self) -> Union[Type[Connection], graphene.NonNull]:
        type_ = super().type
        non_null = isinstance(type_, graphene.NonNull)
        if non_null:  # pragma: no cover
            type_ = type_.of_type

        connection_type: Optional[Type[Connection]] = type_._meta.connection
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
    def underlying_type(self) -> Type[DjangoObjectType]:
        return self.connection_type._meta.node

    @cached_property
    def model(self) -> Type[models.Model]:
        return self.underlying_type._meta.model
