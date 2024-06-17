from __future__ import annotations

import contextlib
from contextlib import suppress

from django.core.exceptions import FieldDoesNotExist
from django.db.models import Field, ForeignKey, Model
from graphene import Connection, ObjectType, PageInfo
from graphene.relay.node import AbstractNode
from graphene.types.definitions import GrapheneObjectType, GrapheneUnionType
from graphene.utils.str_converters import to_snake_case
from graphene_django import DjangoObjectType
from graphql import (
    FieldNode,
    FragmentDefinitionNode,
    FragmentSpreadNode,
    GraphQLField,
    GraphQLOutputType,
    InlineFragmentNode,
    SelectionNode,
)
from graphql.execution.execute import get_field_def

from .errors import OptimizerError
from .settings import optimizer_settings
from .typing import GRAPHQL_BUILTIN, GQLInfo, ModelField, Optional, ToManyField, ToOneField, TypeGuard, Union, overload

__all__ = [
    "GraphQLASTWalker",
]


GrapheneType = Union[GrapheneObjectType, GrapheneUnionType]
Selections = tuple[SelectionNode, ...]


class GraphQLASTWalker:
    """Class for walking the GraphQL AST and handling the different nodes."""

    def __init__(self, info: GQLInfo, model: Optional[type[Model]] = None) -> None:
        self.info = info
        self.complexity: int = 0
        self.model: type[Model] = model

    def increase_complexity(self) -> None:
        self.complexity += 1

    def run(self) -> None:
        selections: Selections = self.info.field_nodes  # type: ignore[assignment]
        field_type: GrapheneObjectType = self.info.parent_type  # type: ignore[assignment]
        return self.handle_selections(field_type, selections)

    def handle_selections(self, field_type: GrapheneType, selections: Selections) -> None:
        for selection in selections:
            if isinstance(selection, FieldNode):
                self.handle_field_node(field_type, selection)

            elif isinstance(selection, FragmentSpreadNode):
                self.handle_fragment_spread(field_type, selection)

            elif isinstance(selection, InlineFragmentNode):
                self.handle_inline_fragment(field_type, selection)

            else:  # pragma: no cover
                msg = f"Unhandled selection node: '{selection}'"
                raise OptimizerError(msg)

    def handle_field_node(self, field_type: GrapheneObjectType, field_node: FieldNode) -> None:
        graphene_type: type[ObjectType] = field_type.graphene_type

        if self.info.parent_type == field_type:
            return self.handle_query_class(field_type, field_node)

        if issubclass(graphene_type, Connection):
            return self.handle_connection(field_type, field_node)

        if is_edge(field_type):
            return self.handle_edge(field_type, field_node)

        if issubclass(graphene_type, PageInfo):  # pragma: no cover
            return self.handle_page_info(field_type, field_node)

        if issubclass(graphene_type, ObjectType):
            return self.handle_object_type(field_type, field_node)

        msg = f"Unhandled graphene type: '{graphene_type}'"  # pragma: no cover
        raise OptimizerError(msg)  # pragma: no cover

    def handle_query_class(self, field_type: GrapheneObjectType, field_node: FieldNode) -> None:
        graphene_type = self.get_graphene_type(field_type, field_node)
        selections = get_selections(field_node)
        return self.handle_selections(graphene_type, selections)

    def handle_object_type(self, field_type: GrapheneObjectType, field_node: FieldNode) -> None:
        field_name = to_snake_case(field_node.name.value)
        if is_graphql_builtin(field_name):
            return self.handle_graphql_builtin(field_type, field_node)

        graphene_type: type[ObjectType] = field_type.graphene_type

        if issubclass(graphene_type, DjangoObjectType):
            return self.handle_model_field(field_type, field_node, field_name)
        return self.handle_plain_object_type(field_type, field_node)

    def handle_graphql_builtin(self, field_type: GrapheneObjectType, field_node: FieldNode) -> None: ...

    def handle_plain_object_type(self, field_type: GrapheneObjectType, field_node: FieldNode) -> None: ...

    def handle_model_field(self, field_type: GrapheneObjectType, field_node: FieldNode, field_name: str) -> None:
        model: type[Model] = field_type.graphene_type._meta.model
        field = get_model_field(model, field_name)

        if field is None:
            with self.use_model(model):
                return self.handle_custom_field(field_type, field_node)

        if not field.is_relation or is_foreign_key_id(field, field_node):
            with self.use_model(model):
                return self.handle_normal_field(field_type, field_node, field)

        if is_to_one(field):
            related_model = get_related_model(field, model)
            with self.use_model(field.model):
                return self.handle_to_one_field(field_type, field_node, field, related_model)

        if is_to_many(field):
            related_model = get_related_model(field, model)
            with self.use_model(model):
                return self.handle_to_many_field(field_type, field_node, field, related_model)

        msg = f"Unhandled field: '{field.name}'"  # pragma: no cover
        raise OptimizerError(msg)  # pragma: no cover

    def handle_custom_field(self, field_type: GrapheneObjectType, field_node: FieldNode) -> None: ...

    def handle_normal_field(self, field_type: GrapheneObjectType, field_node: FieldNode, field: Field) -> None: ...

    def handle_to_one_field(
        self,
        field_type: GrapheneObjectType,
        field_node: FieldNode,
        related_field: ToOneField,
        related_model: type[Model] | None,
    ) -> None:
        graphene_type = self.get_graphene_type(field_type, field_node)
        selections = get_selections(field_node)
        self.increase_complexity()
        return self.handle_selections(graphene_type, selections)

    def handle_to_many_field(
        self,
        field_type: GrapheneObjectType,
        field_node: FieldNode,
        related_field: ToManyField,
        related_model: type[Model] | None,
    ) -> None:
        graphene_type = self.get_graphene_type(field_type, field_node)
        selections = get_selections(field_node)
        self.increase_complexity()
        return self.handle_selections(graphene_type, selections)

    def handle_connection(self, field_type: GrapheneObjectType, field_node: FieldNode) -> None:
        if field_node.name.value == optimizer_settings.TOTAL_COUNT_FIELD:
            return self.handle_total_count(field_type, field_node)

        graphene_type = self.get_graphene_type(field_type, field_node)
        selections = get_selections(field_node)
        return self.handle_selections(graphene_type, selections)

    def handle_edge(self, field_type: GrapheneObjectType, field_node: FieldNode) -> None:
        graphene_type = self.get_graphene_type(field_type, field_node)
        selections = get_selections(field_node)
        return self.handle_selections(graphene_type, selections)

    def handle_total_count(self, field_type: GrapheneObjectType, field_node: FieldNode) -> None: ...

    def handle_page_info(self, field_type: GrapheneObjectType, field_node: FieldNode) -> None: ...

    def handle_fragment_spread(self, field_type: GrapheneObjectType, fragment_spread: FragmentSpreadNode) -> None:
        name = fragment_spread.name.value
        fragment_definition = self.info.fragments[name]
        selections = get_selections(fragment_definition)
        return self.handle_selections(field_type, selections)

    def handle_inline_fragment(self, field_type: GrapheneUnionType, inline_fragment: InlineFragmentNode) -> None:
        fragment_type = get_fragment_type(field_type, inline_fragment)
        fragment_model: type[Model] = fragment_type.graphene_type._meta.model
        if fragment_model != self.model:
            return None

        selections = get_selections(inline_fragment)
        return self.handle_selections(fragment_type, selections)

    def get_graphene_type(self, field_type: GrapheneObjectType, field_node: FieldNode) -> GrapheneType:
        graphql_field = get_field_def(self.info.schema, field_type, field_node)
        return get_underlying_type(graphql_field.type)

    def get_field_name(self, field_node: FieldNode) -> str:
        alias = getattr(field_node.alias, "value", None)
        return alias or to_snake_case(field_node.name.value)

    @contextlib.contextmanager
    def use_model(self, model: type[Model]) -> GraphQLASTWalker:
        orig_model = self.model
        try:
            self.model = model
            yield
        finally:
            self.model = orig_model


@overload
def get_underlying_type(
    field_type: type[GraphQLOutputType],
) -> type[Union[DjangoObjectType, GrapheneObjectType]]: ...  # pragma: no cover


@overload
def get_underlying_type(
    field_type: GraphQLOutputType,
) -> Union[DjangoObjectType, GrapheneObjectType]: ...  # pragma: no cover


def get_underlying_type(field_type):
    while hasattr(field_type, "of_type"):
        field_type = field_type.of_type
    return field_type


def get_selections(field_node: Union[FieldNode, FragmentDefinitionNode, InlineFragmentNode]) -> Selections:
    return getattr(field_node.selection_set, "selections", ())


def is_edge(field_type: GrapheneObjectType) -> bool:
    # Edge-classes are created by `graphene.relay.connection.get_edge_class`,
    # which means that we cannot check against the EdgeBase class directly.
    return all(field in field_type.fields for field in ["node", "cursor"]) and field_type.name.endswith("Edge")


def is_connection(graphql_field: Union[GraphQLField, GrapheneObjectType]) -> bool:
    return issubclass(getattr(graphql_field, "graphene_type", type(None)), Connection)


def is_node(graphql_field: GraphQLField) -> bool:
    return issubclass(getattr(getattr(graphql_field.resolve, "func", None), "__self__", type(None)), AbstractNode)


def is_graphql_builtin(field_name: str) -> bool:
    return field_name.lower() in GRAPHQL_BUILTIN


def is_foreign_key_id(field: Field, field_node: FieldNode) -> bool:
    return isinstance(field, ForeignKey) and field.get_attname() == to_snake_case(field_node.name.value)


def is_to_many(field: Field) -> TypeGuard[ToManyField]:
    return bool(field.one_to_many or field.many_to_many)


def is_to_one(field: Field) -> TypeGuard[ToOneField]:
    return bool(field.many_to_one or field.one_to_one)


def get_fragment_type(field_type: GrapheneUnionType, inline_fragment: InlineFragmentNode) -> GrapheneObjectType:
    fragment_type_name = inline_fragment.type_condition.name.value
    gen = (t for t in field_type.types if t.name == fragment_type_name)
    fragment_type: Optional[GrapheneObjectType] = next(gen, None)

    if fragment_type is None:  # pragma: no cover
        msg = f"Fragment type '{fragment_type_name}' not found in union '{field_type}'"
        raise OptimizerError(msg)

    return fragment_type


def get_related_model(related_field: Union[ToOneField, ToManyField], model: type[Model]) -> type[Model] | None:
    """
    Get the related model for a field.
    Note: For generic foreign keys, the related model is unknown (=None).
    """
    related_model = related_field.related_model
    if related_model == "self":  # pragma: no cover
        return model
    return related_model  # type: ignore[return-value]


def get_model_field(model: type[Model], field_name: str) -> Optional[ModelField]:
    if field_name == "pk":
        model_field: ModelField = model._meta.pk
        return model_field

    with suppress(FieldDoesNotExist):
        model_field: ModelField = model._meta.get_field(field_name)
        return model_field

    # Field might be a reverse many-related field without `related_name`, in which case
    # the `model._meta.fields_map` will store the relation without the "_set" suffix.
    if field_name.endswith("_set"):
        with suppress(FieldDoesNotExist):
            model_field: ModelField = model._meta.get_field(field_name.removesuffix("_set"))
            if is_to_many(model_field):
                return model_field

    return None
