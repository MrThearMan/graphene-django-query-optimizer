from __future__ import annotations

import contextlib
from typing import TYPE_CHECKING

import graphene
from graphene.utils.str_converters import to_snake_case
from graphene_django.settings import graphene_settings
from graphene_django.utils import DJANGO_FILTER_INSTALLED
from graphql import FieldNode, get_argument_values
from graphql.execution.execute import get_field_def

from .ast import GrapheneType, GraphQLASTWalker, Selections, get_underlying_type, is_connection, is_node
from .typing import GQLInfo, GraphQLFilterInfo, ToManyField, ToOneField
from .utils import swappable_by_subclassing

if TYPE_CHECKING:
    from django.db.models import Model
    from graphene.types.definitions import GrapheneObjectType

    from .typing import Any, Optional


__all__ = [
    "get_filter_info",
]


def get_filter_info(info: GQLInfo, model: type[Model]) -> GraphQLFilterInfo:
    """Compile filter information included in the GraphQL query."""
    compiler = FilterInfoCompiler(info, model)
    compiler.run()
    # Return the compiled filter info, or an empty dict if there is no filter info.
    name = getattr(info.field_nodes[0].alias, "value", None) or to_snake_case(info.field_name)
    return compiler.filter_info.get(name, {})


@swappable_by_subclassing
class FilterInfoCompiler(GraphQLASTWalker):
    """Class for compiling filtering information from a GraphQL query."""

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        self.filter_info: dict[str, GraphQLFilterInfo] = {}
        super().__init__(*args, **kwargs)

    def add_filter_info(self, parent_type: GrapheneObjectType, field_node: FieldNode) -> None:
        """
        Adds filter info for a field.
        Called for all field nodes that match a database relation.

        :param parent_type: Parent object type.
        :param field_node: FieldNode for the relation.
        """
        graphql_field = get_field_def(self.info.schema, parent_type, field_node)
        graphene_type = get_underlying_type(graphql_field.type)

        field_name = self.get_field_name(field_node)
        orig_field_name = to_snake_case(field_node.name.value)
        filters = get_argument_values(graphql_field, field_node, self.info.variable_values)

        is_node_ = is_node(graphql_field)
        is_connection_ = is_connection(graphene_type)

        # Find the field-specific limit, or use the default limit.
        max_limit: Optional[int] = getattr(
            getattr(parent_type.graphene_type, orig_field_name, None),
            "max_limit",
            graphene_settings.RELAY_CONNECTION_MAX_LIMIT,
        )

        self.filter_info[field_name] = GraphQLFilterInfo(
            name=graphene_type.name,
            # If the field is a relay node field, its `id` field should not be counted as a filter.
            filters={} if is_node_ else filters,
            children={},
            filterset_class=None,
            is_connection=is_connection_,
            is_node=is_node_,
            max_limit=max_limit,
        )

        if DJANGO_FILTER_INSTALLED and hasattr(graphene_type, "graphene_type"):
            object_type = graphene_type.graphene_type
            if is_connection_:
                object_type = object_type._meta.node

            self.filter_info[field_name]["filterset_class"] = getattr(object_type._meta, "filterset_class", None)

    def handle_selections(self, field_type: GrapheneType, selections: Selections) -> None:
        super().handle_selections(field_type, selections)
        # Remove filter info that do not have filters or children.
        # Preserve filter info for connections so that default nested limiting can be applied.
        for name in list(self.filter_info):
            info = self.filter_info[name]
            if not (info["filters"] or info["children"] or info["is_connection"]):
                del self.filter_info[name]

    def handle_query_class(self, field_type: GrapheneObjectType, field_node: FieldNode) -> None:
        self.add_filter_info(field_type, field_node)
        with self.child_filter_info(field_node):
            super().handle_query_class(field_type, field_node)

    def handle_custom_field(self, field_type: GrapheneObjectType, field_node: FieldNode) -> None:
        field_name = to_snake_case(field_node.name.value)
        field = getattr(field_type.graphene_type, field_name, None)
        if isinstance(field, graphene.Field):
            self.add_filter_info(field_type, field_node)

    def handle_to_one_field(
        self,
        field_type: GrapheneObjectType,
        field_node: FieldNode,
        related_field: ToOneField,
        related_model: type[Model] | None,
    ) -> None:
        self.add_filter_info(field_type, field_node)
        with self.child_filter_info(field_node):
            return super().handle_to_one_field(field_type, field_node, related_field, related_model)

    def handle_to_many_field(
        self,
        field_type: GrapheneObjectType,
        field_node: FieldNode,
        related_field: ToManyField,
        related_model: type[Model] | None,
    ) -> None:
        self.add_filter_info(field_type, field_node)
        with self.child_filter_info(field_node):
            return super().handle_to_many_field(field_type, field_node, related_field, related_model)

    @contextlib.contextmanager
    def child_filter_info(self, field_node: FieldNode) -> None:
        field_name = self.get_field_name(field_node)
        arguments: dict[str, GraphQLFilterInfo] = {}
        orig_arguments = self.filter_info
        try:
            self.filter_info = arguments
            yield
        finally:
            self.filter_info = orig_arguments
            if arguments:
                self.filter_info[field_name]["children"] = arguments
