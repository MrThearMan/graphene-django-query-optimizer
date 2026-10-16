from __future__ import annotations

from unittest.mock import Mock, patch

import pytest
from graphene.types.definitions import GrapheneUnionType

from example_project.app.models import Example
from query_optimizer.ast import GraphQLASTWalker, get_fragment_type, get_model_field
from query_optimizer.errors import OptimizerError


def test_ast_walker__unhandled_selection_node():
    walker = GraphQLASTWalker(info=Mock())

    with pytest.raises(OptimizerError, match="Unhandled selection node"):
        walker.handle_selections(field_type=Mock(), selections=(Mock(),))


def test_ast_walker__unhandled_graphene_type():
    walker = GraphQLASTWalker(info=Mock())
    field_type = Mock(graphene_type=int)

    with pytest.raises(OptimizerError, match="Unhandled graphene type"):
        walker.handle_field_node(field_type=field_type, field_node=Mock())


def test_ast_walker__unhandled_model_field():
    walker = GraphQLASTWalker(info=Mock())
    field_type = Mock()
    field_type.graphene_type._meta.model = Example
    field = Mock(is_relation=True, many_to_one=False, one_to_one=False, one_to_many=False, many_to_many=False)
    field.name = "foo"

    with (
        patch("query_optimizer.ast.get_model_field", return_value=field),
        pytest.raises(OptimizerError, match="Unhandled field: 'foo'"),
    ):
        walker.handle_model_field(field_type=field_type, field_node=Mock(), field_name="foo")


def test_get_fragment_type__not_in_union():
    field_type = Mock(spec=GrapheneUnionType, types=[])
    inline_fragment = Mock()
    inline_fragment.type_condition.name.value = "Foo"

    with pytest.raises(OptimizerError, match="Fragment type 'Foo' not found in union"):
        get_fragment_type(field_type, inline_fragment, schema=Mock())


def test_get_fragment_type__not_in_schema():
    inline_fragment = Mock()
    inline_fragment.type_condition.name.value = "Foo"
    schema = Mock()
    schema.get_type.return_value = None

    with pytest.raises(OptimizerError, match="Fragment type 'Foo' not found in schema"):
        get_fragment_type(Mock(), inline_fragment, schema=schema)


def test_get_model_field__set_suffix_for_to_one_field():
    assert get_model_field(Example, "forward_one_to_one_field_set") is None
