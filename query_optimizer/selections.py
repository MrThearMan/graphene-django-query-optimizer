from __future__ import annotations

import contextlib
from typing import TYPE_CHECKING

from graphene.utils.str_converters import to_snake_case

from query_optimizer.ast import GraphQLASTWalker, get_selections

from .utils import swappable_by_subclassing

if TYPE_CHECKING:
    from django.db import models
    from graphene.types.definitions import GrapheneObjectType
    from graphql import FieldNode

    from .typing import Any, GQLInfo, Optional, ToManyField, ToOneField


__all__ = [
    "get_field_selections",
]


def get_field_selections(info: GQLInfo, model: Optional[type[models.Model]] = None) -> list[Any]:
    """Compile filter information included in the GraphQL query."""
    compiler = FieldSelectionCompiler(info, model)
    compiler.run()
    return compiler.field_selections[0][to_snake_case(info.field_name)]


@swappable_by_subclassing
class FieldSelectionCompiler(GraphQLASTWalker):
    """Class for compiling filtering information from a GraphQL query."""

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        self.field_selections: list[Any] = []
        super().__init__(*args, **kwargs)

    def handle_query_class(self, field_type: GrapheneObjectType, field_node: FieldNode) -> None:
        with self.child_selections(field_node):
            return super().handle_query_class(field_type, field_node)

    def handle_graphql_builtin(self, field_type: GrapheneObjectType, field_node: FieldNode) -> None:
        self.field_selections.append(to_snake_case(field_node.name.value))  # pragma: no cover

    def handle_plain_object_type(self, field_type: GrapheneObjectType, field_node: FieldNode) -> None:
        selections = get_selections(field_node)

        if not selections:
            self.field_selections.append(to_snake_case(field_node.name.value))
            return None

        graphene_type = self.get_graphene_type(field_type, field_node)
        with self.child_selections(field_node):
            return self.handle_selections(graphene_type, selections)

    def handle_normal_field(self, field_type: GrapheneObjectType, field_node: FieldNode, field: models.Field) -> None:
        self.field_selections.append(to_snake_case(field_node.name.value))

    def handle_custom_field(self, field_type: GrapheneObjectType, field_node: FieldNode) -> None:
        self.field_selections.append(to_snake_case(field_node.name.value))  # pragma: no cover

    def handle_to_one_field(
        self,
        field_type: GrapheneObjectType,
        field_node: FieldNode,
        related_field: ToOneField,
        related_model: type[models.Model] | None,
    ) -> None:
        with self.child_selections(field_node):
            return super().handle_to_many_field(field_type, field_node, related_field, related_model)

    def handle_to_many_field(
        self,
        field_type: GrapheneObjectType,
        field_node: FieldNode,
        related_field: ToManyField,
        related_model: type[models.Model] | None,
    ) -> None:
        with self.child_selections(field_node):
            return super().handle_to_one_field(field_type, field_node, related_field, related_model)

    @contextlib.contextmanager
    def child_selections(self, field_node: FieldNode) -> None:
        field_name = to_snake_case(field_node.name.value)
        selections: list[Any] = []
        orig_selections = self.field_selections
        try:
            self.field_selections = selections
            yield
        finally:
            self.field_selections = orig_selections
            if selections:
                self.field_selections.append({field_name: selections})
