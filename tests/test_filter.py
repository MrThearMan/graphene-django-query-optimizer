from __future__ import annotations

from unittest.mock import Mock

from example_project.app.types import BuildingFilterSet
from query_optimizer.filter import default_filterset_class
from query_optimizer.filter_info import FilterInfoCompiler


def test_default_filterset_class__from_settings(settings):
    settings.GRAPHQL_QUERY_OPTIMIZER = {"DEFAULT_FILTERSET_CLASS": "example_project.app.types.BuildingFilterSet"}
    default_filterset_class.cache_clear()
    try:
        assert default_filterset_class() is BuildingFilterSet
    finally:
        default_filterset_class.cache_clear()


def test_filter_info__custom_field__not_a_graphene_field():
    compiler = FilterInfoCompiler(info=Mock())
    field_node = Mock()
    field_node.name.value = "foo"

    compiler.handle_custom_field(field_type=Mock(graphene_type=object), field_node=field_node)

    assert compiler.filter_info == {}
