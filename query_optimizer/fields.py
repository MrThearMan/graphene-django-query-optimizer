# ruff: noqa: UP006
from __future__ import annotations

import warnings
from functools import cached_property, partial
from typing import TYPE_CHECKING

import graphene
from graphene.relay.connection import connection_adapter, page_info_adapter
from graphene.types.argument import to_arguments
from graphene.utils.str_converters import to_camel_case, to_snake_case
from graphene_django.settings import graphene_settings
from graphene_django.utils.utils import DJANGO_FILTER_INSTALLED, maybe_queryset
from graphql_relay.connection.array_connection import offset_to_cursor

from .ast import get_underlying_type
from .compiler import OptimizationCompiler, optimize
from .prefetch_hack import fetch_in_context
from .settings import optimizer_settings
from .utils import calculate_queryset_slice, is_optimized
from .validators import validate_pagination_args

if TYPE_CHECKING:
    from django.db import models
    from django.db.models import Model, QuerySet
    from django.db.models.manager import Manager
    from graphene.relay.connection import Connection
    from graphql_relay import EdgeType
    from graphql_relay.connection.connection import ConnectionType

    from .optimizer import QueryOptimizer
    from .types import DjangoObjectType
    from .typing import (
        Any,
        ArgTypeInput,
        Callable,
        ConnectionResolver,
        ExpressionKind,
        GQLInfo,
        Iterable,
        ManualOptimizerMethod,
        ModelResolver,
        ObjectTypeInput,
        Optional,
        QuerySetResolver,
        Type,
        Union,
        UnmountedTypeInput,
    )

__all__ = [
    "AnnotatedField",
    "DjangoConnectionField",
    "DjangoListField",
    "ManuallyOptimizedField",
    "MultiField",
    "RelatedField",
]


class RelatedField(graphene.Field):
    """Field for `to-one` related models with default resolvers."""

    def __init__(
        self,
        type_: ObjectTypeInput,
        /,
        *,
        field_name: Optional[str] = None,
        **kwargs: Any,
    ) -> None:
        """
        Initialize a related field for the given type.

        :param type_: DjangoObjectType the related field is for.
                      This can also be a dot import path to the object type,
                      or a callable that returns the object type.
        :param field_name: The name of the model field or related accessor this related field is for.
                           Only needed if the field name on the ObjectType this field is
                           defined on is different from the field name on the model.
        :param kwargs: Extra arguments passed to `graphene.types.field.Field`.
        """
        if kwargs.pop("reverse", None) is not None:  # pragma: no cover
            msg = (
                "The `reverse` argument is no longer required, and should be removed. "
                "This will become an error in the future."
            )
            warnings.warn(msg, category=DeprecationWarning, stacklevel=1)

        self.field_name = field_name
        super().__init__(type_, **kwargs)

    def wrap_resolve(self, parent_resolver: ModelResolver) -> ModelResolver:
        # Allow user defined resolvers to override the default behavior.
        if not isinstance(parent_resolver, partial):
            return parent_resolver
        return self.related_resolver

    def related_resolver(self, root: models.Model, info: GQLInfo) -> Optional[models.Model]:
        field_name = self.field_name or to_snake_case(info.field_name)
        # Related object should be optimized to the root model.
        related_instance: Optional[models.Model] = getattr(root, field_name, None)
        if related_instance is None:  # pragma: no cover
            return None
        self.underlying_type.run_instance_checks(related_instance, info)
        return related_instance

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
    """DjangoListField that also supports filtering."""

    def __init__(
        self,
        type_: ObjectTypeInput,
        /,
        *,
        no_filters: bool = False,
        field_name: Optional[str] = None,
        **kwargs: Any,
    ) -> None:
        """
        Initialize a list field for the given type.

        :param type_: DjangoObjectType the list field is for.
                      This can also be a dot import path to the object type,
                      or a callable that returns the object type.
        :param no_filters: Should filterset filters be disabled for this field?
        :param field_name: The name of the model field or related accessor this list field is for.
                           Only needed if the field name on the ObjectType this field is
                           defined on is different from the field name on the model.
        :param kwargs: Extra arguments passed to `graphene.types.field.Field`.
        """
        self.no_filters = no_filters
        self.field_name = field_name
        if isinstance(type_, graphene.NonNull):  # pragma: no cover
            type_ = type_.of_type
        super().__init__(graphene.List(graphene.NonNull(type_)), **kwargs)

    def wrap_resolve(self, parent_resolver: QuerySetResolver) -> QuerySetResolver:
        self.resolver = parent_resolver
        return self.list_resolver

    def list_resolver(self, root: Any, info: GQLInfo, **kwargs: Any) -> models.QuerySet:
        # If field is aliased, a prefetch should have been done to that alias.
        # If not, call the ObjectType's "resolve_{field_name}" method, if it exists.
        # Otherwise, call the default resolver (usually `dict_or_attr_resolver`).
        alias = getattr(info.field_nodes[0].alias, "value", None)
        result = (
            getattr(root, alias)
            # Aliases don't matter at the root level, since we don't need to
            # distinguish them from a parent model prefetches.
            if root != info.root_value and alias is not None
            else self.resolver(root, info, **kwargs)
        )

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
    """DjangoConnectionField for Django models that works for both filtered and non-filtered Relay-nodes."""

    def __init__(
        self,
        type_: ObjectTypeInput,
        /,
        *,
        max_limit: Optional[int] = ...,
        no_filters: bool = False,
        field_name: Optional[str] = None,
        **kwargs: Any,
    ) -> None:
        """
        Initialize a connection field for the given type.

        :param type_: DjangoObjectType the connection is for.
                      This can also be a dot import path to the object type,
                      or a callable that returns the object type.
        :param max_limit: Maximum number of items that can be requested in a single query for this connection.
                          Set to None to disable the limit.
        :param no_filters: Should filterset filters be disabled for this field?
        :param field_name: The name of the model field or related accessor this connection is for.
                           Only needed if the field name on the ObjectType this field is
                           defined on is different from the field name on the model.
        :param kwargs: Extra arguments passed to `graphene.types.field.Field`.
        """
        # Maximum number of items that can be requested in a single query for this connection.
        # Set to None to disable the limit.
        self.max_limit = max_limit if max_limit is not ... else graphene_settings.RELAY_CONNECTION_MAX_LIMIT
        self.no_filters = no_filters
        self.field_name = field_name

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

        # Save initial pagination information to the request. This can be used if the queryset
        # is large and needs to be evaluated before the optimizer does so.
        if not hasattr(info.context, "optimizer_pagination"):
            info.context.optimizer_pagination = {}
        name = to_snake_case(info.field_name)
        info.context.optimizer_pagination[name] = pagination_args

        # If field is aliased, a prefetch should have been done to that alias.
        # If not, call the ObjectType's "resolve_{field_name}" method, if it exists.
        # Otherwise, call the default resolver (usually `dict_or_attr_resolver`).
        alias = getattr(info.field_nodes[0].alias, "value", None)
        result = (
            getattr(root, alias)
            # Aliases don't matter at the root level, since we don't need to
            # distinguish them from a parent model prefetches.
            if root != info.root_value and alias is not None
            else self.resolver(root, info, **kwargs)
        )

        queryset = self.to_queryset(result)
        queryset = self.underlying_type.get_queryset(queryset, info)

        max_complexity: Optional[int] = getattr(self.underlying_type._meta, "max_complexity", None)

        # Note if the queryset has already been optimized.
        already_optimized = is_optimized(queryset)

        optimizer = OptimizationCompiler(info, max_complexity=max_complexity).compile(queryset)
        if optimizer is not None:
            queryset = optimizer.optimize_queryset(queryset)

        # Queryset optimization contains filtering, so we count after optimization.
        pagination_args["size"] = count = (
            queryset.count()
            if not already_optimized
            # Prefetch(..., to_attr=...) will return a list of models.
            # TODO: This might be wrong.
            else len(queryset)
            if isinstance(queryset, list)
            # If this is a nested connection field, prefetch queryset models should have been
            # annotated with the queryset count (pick it from the first one).
            else getattr(
                next(iter(getattr(queryset, "_result_cache", []) or []), None),
                optimizer_settings.PREFETCH_COUNT_KEY,
                0,  # QuerySet result cache is empty -> count is 0.
            )
        )
        cut = calculate_queryset_slice(**pagination_args)

        # Prefetch queryset has already been sliced.
        if not already_optimized:
            queryset = queryset[cut]

        edges: list[EdgeType] = [
            # Create a connection from the sliced queryset.
            self.connection_type.Edge(node=value, cursor=offset_to_cursor(cut.start + index))
            for index, value in enumerate(fetch_in_context(queryset))
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


class AnnotatedField(graphene.Field):
    """Field for resolving Django ORM expressions that the optimizer will annotate to the queryset."""

    def __init__(
        self,
        type_: UnmountedTypeInput,
        /,
        expression: ExpressionKind,
        aliases: Optional[dict[str, ExpressionKind]] = None,
        extra_annotations: Optional[dict[str, ExpressionKind]] = None,
        **kwargs: Any,
    ) -> None:
        self.expression = expression
        self.aliases = aliases
        self.extra_annotations = extra_annotations
        super().__init__(type_, **kwargs)

    def __set_name__(self, owner: type[DjangoObjectType], name: str) -> None:
        self.name = to_camel_case(name)

    def wrap_resolve(self, parent_resolver: Callable[..., Any]) -> Callable[..., Any]:
        # `parent_resolver` is either a `resolve_{self.name}` method defined
        # on the owner class, or a partial of `dict_or_attr_resolver`.
        self.resolver = parent_resolver
        return self.annotation_resolver

    def annotation_resolver(self, root: Model, info: GQLInfo, **kwargs: Any) -> Any:
        return self.resolver(root, info, **kwargs)

    def optimizer_hook(self, compiler: OptimizationCompiler) -> None:
        compiler.optimizer.annotations[to_snake_case(self.name)] = self.expression
        if self.aliases is not None:
            compiler.optimizer.aliases.update(self.aliases)
        if self.extra_annotations is not None:  # pragma: no cover
            compiler.optimizer.annotations.update(self.extra_annotations)


class MultiField(graphene.Field):
    """Field that requires multiple model fields to resolve. Does not support related lookups."""

    def __init__(self, type_: UnmountedTypeInput, /, fields: Iterable[str], **kwargs: Any) -> None:
        self.fields = fields
        super().__init__(type_, **kwargs)

    def __set_name__(self, owner: type[DjangoObjectType], name: str) -> None:
        self.name = to_camel_case(name)

    def wrap_resolve(self, parent_resolver: Callable[..., Any]) -> Callable[..., Any]:
        # `parent_resolver` is either a `resolve_{self.name}` method defined
        # on the owner class, or a partial of `dict_or_attr_resolver`.
        self.resolver = parent_resolver
        return self.multi_field_resolver

    def multi_field_resolver(self, root: Model, info: GQLInfo, **kwargs: Any) -> Any:
        return self.resolver(root, info, **kwargs)

    def optimizer_hook(self, compiler: OptimizationCompiler) -> None:
        compiler.optimizer.only_fields.extend(self.fields)


class ManuallyOptimizedField(graphene.Field):
    """
    Field that is manually optimized using a method defined on the object type this field is on.

    Must define a `optimize_{name}` staticmethod on the object type, where `{name}` is the name
    of the field defined on the object type. This method takes the following arguments:

    - `queryset`: The QuerySet to optimize.
    - `optimizer`: The QueryOptimizer instance that is performing the optimizations.
    - `**kwargs`: Filters passed to the field (see `args` in __init__).

    The optimizer will run these methods as the last filtering step.
    """

    def __init__(
        self,
        type_: UnmountedTypeInput,
        /,
        *,
        args: dict[str, ArgTypeInput] | None = None,
        **kwargs: Any,
    ) -> None:
        self.optimizer: ManualOptimizerMethod | None = None
        super().__init__(type_, args=args, **kwargs)

    def __set_name__(self, object_type: type[DjangoObjectType], name: str) -> None:
        self.name = to_camel_case(name)
        resolver_name = f"optimize_{name}"
        self.optimizer = getattr(object_type, resolver_name, None)
        if self.optimizer is None:  # pragma: no cover
            msg = f"Optimizer method '{resolver_name}' missing from '{object_type}'."
            raise AttributeError(msg)

    def optimize(self, queryset: QuerySet, optimizer: QueryOptimizer, **kwargs: Any) -> QuerySet:
        return self.optimizer(queryset, optimizer, **kwargs)

    def wrap_resolve(self, parent_resolver: Callable[..., Any]) -> Callable[..., Any]:
        # `parent_resolver` is either a `resolve_{self.name}` method defined
        # on the owner class, or a partial of `dict_or_attr_resolver`.
        self.resolver = parent_resolver
        return self.field_resolver

    def field_resolver(self, root: Model, info: GQLInfo, **kwargs: Any) -> Any:
        return self.resolver(root, info, **kwargs)

    def optimizer_hook(self, compiler: OptimizationCompiler) -> None:
        compiler.optimizer.manual_optimizers[to_snake_case(self.name)] = self.optimize
