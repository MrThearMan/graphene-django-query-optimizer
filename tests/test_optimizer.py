from __future__ import annotations

import logging
from unittest.mock import Mock, patch

import pytest
from django.core.exceptions import ValidationError
from django_filters import FilterSet, NumberFilter

from example_project.app.models import Example, HousingCompany
from query_optimizer.optimizer import OptimizationResults, QueryOptimizer


def test_optimization_results__add__string_prefetch():
    results = OptimizationResults(queryset=Example.objects.all())
    nested_results = OptimizationResults(queryset=Example.objects.all(), name="foo", prefetch_related=["bar"])

    results += nested_results

    assert results.select_related == ["foo"]
    assert results.prefetch_related == ["foo__bar"]


def test_optimizer__object_type_not_registered():
    optimizer = QueryOptimizer(model=Example, info=Mock())
    queryset = Example.objects.all()
    registry = Mock()
    registry.get_type_for_model.return_value = None

    with patch("query_optimizer.optimizer.get_global_registry", return_value=registry):
        assert optimizer.pre_processing(queryset) is queryset
        assert optimizer.filter_queryset(queryset, filter_info={}) is queryset


def test_optimizer__filter_queryset__invalid_filters():
    class ExampleFilterSet(FilterSet):
        number = NumberFilter(field_name="pk")

        class Meta:
            model = Example
            fields = []

    optimizer = QueryOptimizer(model=Example, info=Mock())
    filter_info = {"filterset_class": ExampleFilterSet, "filters": {"number": "foo"}}

    with pytest.raises(ValidationError, match="Enter a number"):
        optimizer.filter_queryset(Example.objects.all(), filter_info=filter_info)


def test_optimizer__paginate_prefetch_queryset__field_not_found(caplog):
    parent = QueryOptimizer(model=Example, info=Mock())
    optimizer = QueryOptimizer(model=HousingCompany, info=Mock(), name="foo", parent=parent)
    queryset = HousingCompany.objects.all()

    with caplog.at_level(logging.WARNING, logger="query_optimizer"):
        assert optimizer.paginate_prefetch_queryset(queryset, filter_info={"is_connection": True}) is queryset

    assert "Cannot find field 'foo' on model 'Example'" in caplog.text


def test_optimizer__get_prefetch_ordering__list():
    optimizer = QueryOptimizer(model=Example, info=Mock())
    filter_info = {"filters": {"order_by": ["fooBar", ""]}}

    assert optimizer.get_prefetch_ordering(filter_info, model=Example) == ["foo_bar"]


def test_optimizer__child_optimizers():
    optimizer = QueryOptimizer(model=Example, info=Mock())
    select_optimizer = QueryOptimizer(model=Example, info=Mock(), name="foo", parent=optimizer)
    prefetch_optimizer = QueryOptimizer(model=Example, info=Mock(), name="bar", parent=optimizer)

    assert optimizer.has_child_optimizer("foo") is False
    assert optimizer.get_child_optimizer("foo") is None

    assert optimizer.get_or_set_child_optimizer("foo", select_optimizer) is select_optimizer
    assert optimizer.get_or_set_child_optimizer("bar", prefetch_optimizer, set_as="prefetch_related") is (
        prefetch_optimizer
    )

    assert optimizer.select_related == {"foo": select_optimizer}
    assert optimizer.prefetch_related == {"bar": prefetch_optimizer}

    assert optimizer.has_child_optimizer("foo") is True
    assert optimizer.has_child_optimizer("bar") is True
    assert optimizer.get_child_optimizer("foo") is select_optimizer
    assert optimizer.get_child_optimizer("bar") is prefetch_optimizer

    new_optimizer = QueryOptimizer(model=Example, info=Mock())
    assert optimizer.get_or_set_child_optimizer("foo", new_optimizer) is select_optimizer
    assert optimizer.get_or_set_child_optimizer("bar", new_optimizer) is prefetch_optimizer
