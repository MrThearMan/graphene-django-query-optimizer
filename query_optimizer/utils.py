from __future__ import annotations

import logging
from functools import wraps
from typing import TYPE_CHECKING

from django.db.models import ForeignKey, QuerySet
from graphene import Connection
from graphene.types.definitions import GrapheneObjectType
from graphene_django import DjangoObjectType
from graphql.execution.execute import get_field_def

from .errors import OptimizerError
from .settings import optimizer_settings

if TYPE_CHECKING:
    from graphql import GraphQLOutputType, SelectionNode

    from .typing import (
        Callable,
        GQLInfo,
        ModelField,
        Optional,
        ParamSpec,
        ToManyField,
        ToOneField,
        TypeGuard,
        TypeVar,
    )

    T = TypeVar("T")
    P = ParamSpec("P")


__all__ = [
    "get_field_type",
    "get_selections",
    "get_underlying_type",
    "is_foreign_key_id",
    "is_optimized",
    "is_to_many",
    "is_to_one",
    "mark_optimized",
    "mark_unoptimized",
    "maybe_skip_optimization_on_error",
    "optimizer_logger",
]


optimizer_logger = logging.getLogger("query_optimizer")


def is_foreign_key_id(model_field: ModelField, name: str) -> bool:
    return isinstance(model_field, ForeignKey) and model_field.name != name and model_field.get_attname() == name


def get_underlying_type(field_type: GraphQLOutputType) -> GrapheneObjectType:
    while hasattr(field_type, "of_type"):
        field_type = field_type.of_type
    return field_type


def is_to_many(model_field: ModelField) -> TypeGuard[ToManyField]:
    return bool(model_field.one_to_many or model_field.many_to_many)


def is_to_one(model_field: ModelField) -> TypeGuard[ToOneField]:
    return bool(model_field.many_to_one or model_field.one_to_one)


def get_field_type(info: GQLInfo) -> GrapheneObjectType:
    field_node = info.field_nodes[0]
    field_def = get_field_def(info.schema, info.parent_type, field_node)
    return get_underlying_type(field_def.type)


def get_selections(info: GQLInfo) -> tuple[SelectionNode, ...]:
    field_node = info.field_nodes[0]
    selection_set = field_node.selection_set
    return () if selection_set is None else selection_set.selections


def can_optimize(info: GQLInfo) -> bool:
    return_type = get_underlying_type(info.return_type)

    return isinstance(return_type, GrapheneObjectType) and (
        issubclass(return_type.graphene_type, (DjangoObjectType, Connection))
    )


def mark_optimized(queryset: QuerySet) -> None:
    """Mark queryset as optimized so that later optimizers know to skip optimization"""
    queryset._hints[optimizer_settings.OPTIMIZER_MARK] = True  # type: ignore[attr-defined]


def mark_unoptimized(queryset: QuerySet) -> None:  # pragma: no cover
    """Mark queryset as unoptimized so that later optimizers will run optimization"""
    queryset._hints.pop(optimizer_settings.OPTIMIZER_MARK, None)  # type: ignore[attr-defined]


def is_optimized(queryset: QuerySet) -> bool:
    """Has the queryset be optimized?"""
    return queryset._hints.get(optimizer_settings.OPTIMIZER_MARK, False)  # type: ignore[no-any-return, attr-defined]


def maybe_skip_optimization_on_error(func: Callable[P, T]) -> Callable[P, T]:
    @wraps(func)
    def wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
        try:
            return func(*args, **kwargs)
        except OptimizerError:
            raise
        except Exception as error:  # pragma: no cover
            if optimizer_settings.SKIP_OPTIMIZATION_ON_ERROR:
                optimizer_logger.info("Something went wrong during the optimization process.", exc_info=error)
                return args[0]  # original queryset
            raise

    return wrapper


def calculate_queryset_slice(
    *,
    after: Optional[int],
    before: Optional[int],
    first: Optional[int],
    last: Optional[int],
    size: int,
) -> slice:
    """
    Calculate queryset slicing based on the provided arguments.
    Before this, the arguments should be validated so that:
     - `first` and `last`, positive integers or `None`
     - `after` and `before` are non-negative integers or `None`
     - If both `after` and `before` are given, `after` is less than or equal to `before`

    This function is based on the Relay pagination algorithm.
    See. https://relay.dev/graphql/connections.htm#sec-Pagination-algorithm

    :param after: The index after which to start (exclusive).
    :param before: The index before which to stop (exclusive).
    :param first: The number of items to return from the start.
    :param last: The number of items to return from the end (after evaluating first).
    :param size: The total number of items in the queryset.
    """
    #
    # Start from form fetching max number of items.
    #
    start: int = 0
    stop: int = size
    #
    # If `after` is given, change the start index to `after`.
    # If `after` is greater than the current queryset size, change it to `size`.
    #
    if after is not None:
        start = min(after, stop)
    #
    # If `before` is given, change the stop index to `before`.
    # If `before` is greater than the current queryset size, change it to `size`.
    #
    if before is not None:
        stop = min(before, stop)
    #
    # If first is given, and it's smaller than the current queryset size,
    # change the stop index to `start + first`
    # -> Length becomes that of `first`, and the items after it have been removed.
    #
    if first is not None and first < (stop - start):
        stop = start + first
    #
    # If last is given, and it's smaller than the current queryset size,
    # change the start index to `stop - last`.
    # -> Length becomes that of `last`, and the items before it have been removed.
    #
    if last is not None and last < (stop - start):
        start = stop - last

    return slice(start, stop)
