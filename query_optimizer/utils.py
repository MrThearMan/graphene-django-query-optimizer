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
        Collection,
        GQLInfo,
        ModelField,
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
    "unique",
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


def unique(items: Collection[T]) -> list[T]:
    return list(dict.fromkeys(items))


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
    def wrapper(*args: P.args, **kwargs: P.kwargs) -> bool:
        try:
            return func(*args, **kwargs)
        except OptimizerError:
            raise
        except Exception as error:  # pragma: no cover
            if optimizer_settings.DONT_OPTIMIZE_ON_ERROR:
                optimizer_logger.info("Something went wrong during the optimization process.", exc_info=error)
                return args[0]  # original queryset
            raise

    return wrapper
