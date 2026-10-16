from __future__ import annotations

import logging
from unittest.mock import Mock, patch

import graphene
import pytest

from example_project.app.models import Example
from query_optimizer.compiler import OptimizationCompiler, optimize_single
from query_optimizer.utils import mark_optimized
from tests.factories.example import ExampleFactory

pytestmark = [
    pytest.mark.django_db,
]


def test_optimize_single__already_optimized():
    example = ExampleFactory.create()
    queryset = Example.objects.all()
    mark_optimized(queryset)

    assert optimize_single(queryset, info=Mock(), pk=example.pk) == example


def test_compiler__unknown_error():
    compiler = OptimizationCompiler(info=Mock())

    with patch.object(compiler, "run", side_effect=ValueError("foo")), pytest.raises(ValueError, match="foo"):
        compiler.compile(Example.objects.all())


def test_compiler__unknown_error__skip_optimization(settings):
    settings.GRAPHQL_QUERY_OPTIMIZER = {"SKIP_OPTIMIZATION_ON_ERROR": True}
    compiler = OptimizationCompiler(info=Mock())

    with patch.object(compiler, "run", side_effect=ValueError("foo")):
        assert compiler.compile(Example.objects.all()) is None


def test_compiler__page_info__no_total_count_needed():
    compiler = OptimizationCompiler(info=Mock())
    compiler.optimizer = Mock(total_count=False)
    field_node = Mock()
    field_node.name.value = "hasPreviousPage"

    compiler.handle_page_info(field_type=Mock(), field_node=field_node)

    assert compiler.optimizer.total_count is False


def test_compiler__custom_field__not_found(caplog):
    compiler = OptimizationCompiler(info=Mock())
    field_type = Mock()
    field_type.graphene_type._meta.fields = {}
    field_node = Mock()
    field_node.name.value = "foo"

    with caplog.at_level(logging.WARNING, logger="query_optimizer"):
        compiler.handle_custom_field(field_type=field_type, field_node=field_node)

    assert "Field 'foo' not found from object type" in caplog.text


def test_compiler__custom_field__nothing_to_optimize():
    compiler = OptimizationCompiler(info=Mock())
    compiler.optimizer = Mock()
    field_type = Mock()
    field_type.graphene_type._meta.fields = {"foo": graphene.Field(graphene.String)}
    field_node = Mock()
    field_node.name.value = "foo"

    compiler.handle_custom_field(field_type=field_type, field_node=field_node)

    assert compiler.to_attr is None
    assert compiler.optimizer.mock_calls == []
