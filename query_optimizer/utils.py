from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from django.db.models import ForeignKey, QuerySet
from graphene import Connection
from graphene.utils.str_converters import to_snake_case
from graphene_django.utils import DJANGO_FILTER_INSTALLED
from graphql import FieldNode, GraphQLField, GraphQLObjectType, GraphQLSchema, get_argument_values
from graphql.execution.execute import get_field_def

from .settings import optimizer_settings
from .typing import GraphQLFilterInfo, overload

if TYPE_CHECKING:
    from graphene.types.definitions import GrapheneObjectType
    from graphene_django import DjangoObjectType
    from graphql import GraphQLOutputType, SelectionNode

    from .typing import (
        Any,
        FieldNodes,
        GQLInfo,
        ModelField,
        Optional,
        ParamSpec,
        ToManyField,
        ToOneField,
        TypeGuard,
        TypeVar,
        Union,
    )

    T = TypeVar("T")
    P = ParamSpec("P")


__all__ = [
    "get_field_type",
    "get_filter_info",
    "get_selections",
    "get_underlying_type",
    "is_foreign_key_id",
    "is_optimized",
    "is_to_many",
    "is_to_one",
    "mark_optimized",
    "mark_unoptimized",
    "optimizer_logger",
]


optimizer_logger = logging.getLogger("query_optimizer")


def is_foreign_key_id(model_field: ModelField, name: str) -> bool:
    return isinstance(model_field, ForeignKey) and model_field.name != name and model_field.get_attname() == name


@overload
def get_underlying_type(field_type: type[GraphQLOutputType]) -> type[Union[DjangoObjectType, GrapheneObjectType]]:
    ...  # pragma: no cover


@overload
def get_underlying_type(field_type: GraphQLOutputType) -> Union[DjangoObjectType, GrapheneObjectType]:
    ...  # pragma: no cover


def get_underlying_type(field_type):
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


def mark_optimized(queryset: QuerySet) -> None:
    """Mark queryset as optimized so that later optimizers know to skip optimization"""
    queryset._hints[optimizer_settings.OPTIMIZER_MARK] = True  # type: ignore[attr-defined]


def mark_unoptimized(queryset: QuerySet) -> None:  # pragma: no cover
    """Mark queryset as unoptimized so that later optimizers will run optimization"""
    queryset._hints.pop(optimizer_settings.OPTIMIZER_MARK, None)  # type: ignore[attr-defined]


def is_optimized(queryset: QuerySet) -> bool:
    """Has the queryset be optimized?"""
    return queryset._hints.get(optimizer_settings.OPTIMIZER_MARK, False)  # type: ignore[no-any-return, attr-defined]


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


def get_filter_info(info: GQLInfo) -> GraphQLFilterInfo:
    """Find filter arguments from the GraphQL query."""
    args = _get_arguments(info.field_nodes, info.variable_values, info.parent_type, info.schema)
    if not args:
        return {}
    return args[to_snake_case(info.field_name)]


def _get_arguments(
    field_nodes: FieldNodes,
    variable_values: dict[str, Any],
    parent: GraphQLObjectType,
    schema: GraphQLSchema,
) -> dict[str, GraphQLFilterInfo]:
    arguments: dict[str, GraphQLFilterInfo] = {}
    for field_node in field_nodes:
        if not isinstance(field_node, FieldNode):  # pragma: no cover
            continue

        field_def: Optional[GraphQLField] = get_field_def(schema, parent, field_node)
        if field_def is None:  # pragma: no cover
            continue

        name = to_snake_case(field_node.name.value)
        filters = get_argument_values(type_def=field_def, node=field_node, variable_values=variable_values)

        new_parent = get_underlying_type(field_def.type)

        # If the field is a connection, we need to go deeper to get the actual field
        if is_connection := issubclass(getattr(new_parent, "graphene_type", type(None)), Connection):
            field_def = new_parent.fields["edges"]
            new_parent = get_underlying_type(field_def.type)
            field_def = new_parent.fields["node"]
            new_parent = get_underlying_type(field_def.type)
            field_node = field_node.selection_set.selections[0].selection_set.selections[0]  # noqa: PLW2901

        arguments[name] = info = GraphQLFilterInfo(
            name=new_parent.name,
            filters=filters,
            children={},
            filterset_class=None,
            is_connection=is_connection,
        )

        if DJANGO_FILTER_INSTALLED and hasattr(new_parent, "graphene_type"):
            object_type = new_parent.graphene_type
            info["filterset_class"] = getattr(object_type._meta, "filterset_class", None)

        if field_node.selection_set is not None:
            result = _get_arguments(field_node.selection_set.selections, variable_values, new_parent, schema)
            if result:
                info["children"] = result

    return {
        name: field
        for name, field in arguments.items()
        # Remove children that do not have filters or children.
        # Also preserve fields that are connections, so that default limiting can be applied.
        if field["filters"] or field["children"] or field["is_connection"]
    }
