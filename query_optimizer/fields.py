# ruff: noqa: UP006
from __future__ import annotations

from functools import cached_property
from typing import TYPE_CHECKING

import graphene
from graphene.relay.connection import connection_adapter, page_info_adapter
from graphene.types.argument import to_arguments
from graphene.utils.str_converters import to_snake_case
from graphene_django.settings import graphene_settings
from graphene_django.utils.utils import DJANGO_FILTER_INSTALLED, maybe_queryset
from graphql_relay.connection.array_connection import offset_to_cursor

from .ast import get_underlying_type
from .cache import store_in_query_cache
from .compiler import OptimizationCompiler, optimize
from .errors import OptimizerError
from .settings import optimizer_settings
from .utils import calculate_queryset_slice, is_optimized, optimizer_logger
from .validators import validate_pagination_args

if TYPE_CHECKING:
    from django.db import models
    from django.db.models.manager import Manager
    from graphene.relay.connection import Connection
    from graphene_django import DjangoObjectType
    from graphql_relay import EdgeType
    from graphql_relay.connection.connection import ConnectionType

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

    def __init__(self, type_: Union[type[DjangoObjectType], str], *, reverse: bool = False, **kwargs: Any) -> None:
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
        if reverse_object is None:
            return None
        return self.underlying_type.get_node(info, reverse_object.pk)

    @cached_property
    def underlying_type(self) -> type[DjangoObjectType]:
        return get_underlying_type(self.type)


class FilteringMixin:
    # Subclasses should implement the following:
    underlying_type: type[DjangoObjectType]

    no_filters: bool = False
    """Should filterset filters be disabled for this field?"""

    @property
    def args(self) -> dict[str, graphene.Argument]:
        return to_arguments(getattr(self, "_base_args", None) or {}, self.filtering_args)

    @args.setter
    def args(self, args: dict[str, Any]) -> None:
        # noinspection PyAttributeOutsideInit
        self._base_args = args

    @cached_property
    def filtering_args(self) -> Optional[dict[str, graphene.Argument]]:
        if not DJANGO_FILTER_INSTALLED or self.no_filters:  # pragma: no cover
            return None

        from graphene_django.filter.utils import get_filtering_args_from_filterset

        filterset_class = getattr(self.underlying_type._meta, "filterset_class", None)
        if filterset_class is None:
            return None
        return get_filtering_args_from_filterset(filterset_class, self.underlying_type)


class DjangoListField(FilteringMixin, graphene.Field):
    """Django list field that also supports filtering."""

    def __init__(self, type_: Union[Type[DjangoObjectType], str], **kwargs: Any) -> None:
        """
        Initialize a list field for the given type.

        :param type_: Object type or dot import path to the object type.
        :param kwargs:  Extra arguments passed to `graphene.types.field.Field`.
        """
        self.no_filters = kwargs.pop("no_filters", False)
        if isinstance(type_, graphene.NonNull):  # pragma: no cover
            type_ = type_.of_type
        super().__init__(graphene.List(graphene.NonNull(type_)), **kwargs)

    def wrap_resolve(self, parent_resolver: QuerySetResolver) -> QuerySetResolver:
        self.resolver = parent_resolver
        return self.list_resolver

    def list_resolver(self, root: Any, info: GQLInfo, **kwargs: Any) -> models.QuerySet:
        result = self.resolver(root, info, **kwargs)
        queryset = self.to_queryset(result)
        queryset = self.underlying_type.get_queryset(queryset, info)

        max_complexity: Optional[int] = getattr(self.underlying_type._meta, "max_complexity", None)
        return optimize(queryset, info, max_complexity=max_complexity)

    def to_queryset(self, iterable: Union[models.QuerySet, Manager, None]) -> models.QuerySet:
        # Default resolver can return a Manager-instance or None.
        if iterable is None:
            iterable = self.model._default_manager
        return maybe_queryset(iterable)

    @cached_property
    def underlying_type(self) -> type[DjangoObjectType]:
        return get_underlying_type(self.type)

    @cached_property
    def model(self) -> type[models.Model]:
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
        self.max_limit: Optional[int] = kwargs.pop("max_limit", graphene_settings.RELAY_CONNECTION_MAX_LIMIT)
        self.no_filters = kwargs.pop("no_filters", False)

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
        queryset = pre_optimized_queryset = self.underlying_type.get_queryset(queryset, info)

        max_complexity: Optional[int] = getattr(self.underlying_type._meta, "max_complexity", None)

        try:
            # Note if the queryset has already been optimized.
            already_optimized = is_optimized(queryset)

            optimizer = OptimizationCompiler(info, max_complexity=max_complexity).compile(queryset)
            if optimizer is not None:
                queryset = optimizer.optimize_queryset(queryset)

            # Queryset optimization contains filtering, so we count after optimization.
            pagination_args["size"] = count = (
                queryset.count()
                if not already_optimized
                # If this is a nested connection field, prefetch queryset models should have been
                # annotated with the queryset count (pick it from the first one).
                else getattr(
                    next(iter(queryset._result_cache), None),
                    optimizer_settings.PREFETCH_COUNT_KEY,
                    0,  # QuerySet result cache is empty -> count is 0.
                )
            )
            cut = calculate_queryset_slice(**pagination_args)

            # Prefetch queryset has already been sliced.
            if not already_optimized:
                queryset = queryset[cut]

            # Store data in cache after pagination
            if optimizer:
                store_in_query_cache(key=info.operation, queryset=queryset, schema=info.schema, optimizer=optimizer)

        except OptimizerError:  # pragma: no cover
            raise

        except Exception as error:  # noqa: BLE001  # pragma: no cover
            if not optimizer_settings.SKIP_OPTIMIZATION_ON_ERROR:
                raise

            # If an error occurs during optimization, we should still return the unoptimized queryset.
            optimizer_logger.warning("Something went wrong during the optimization process.", exc_info=error)
            queryset = pre_optimized_queryset
            pagination_args["size"] = count = queryset.count()
            cut = calculate_queryset_slice(**pagination_args)
            queryset = queryset[cut]

        # Create a connection from the sliced queryset.
        edges: list[EdgeType] = [
            self.connection_type.Edge(node=value, cursor=offset_to_cursor(cut.start + index))
            for index, value in enumerate(queryset)
        ]
        connection = connection_adapter(
            cls=self.connection_type,
            edges=edges,
            pageInfo=page_info_adapter(
                startCursor=edges[0].cursor if edges else None,
                endCursor=edges[-1].cursor if edges else None,
                hasPreviousPage=cut.start > 0,
                hasNextPage=cut.stop < count,
            ),
        )
        connection.iterable = queryset
        connection.length = count
        return connection

    def to_queryset(self, iterable: Union[models.QuerySet, Manager, None]) -> models.QuerySet:
        # Default resolver can return a Manager-instance or None.
        if iterable is None:
            iterable = self.model._default_manager
        return maybe_queryset(iterable)

    @cached_property
    def type(self) -> Union[Type[Connection], graphene.NonNull]:  # pragma: no cover
        type_ = super().type
        non_null = isinstance(type_, graphene.NonNull)
        if non_null:
            type_ = type_.of_type

        connection_type: Optional[Type[Connection]] = type_._meta.connection
        if connection_type is None:
            msg = f"The type {type_.__name__} doesn't have a connection"
            raise ValueError(msg)

        if non_null:
            return graphene.NonNull(connection_type)
        return connection_type

    @cached_property
    def connection_type(self) -> Type[Connection]:  # pragma: no cover
        type_ = self.type
        if isinstance(type_, graphene.NonNull):
            return type_.of_type
        return type_

    @cached_property
    def underlying_type(self) -> Type[DjangoObjectType]:
        return self.connection_type._meta.node

    @cached_property
    def model(self) -> Type[models.Model]:
        return self.underlying_type._meta.model
