from __future__ import annotations

from typing import Any
from unittest.mock import patch

import pytest
from graphene_django.registry import Registry

from example_project.app.models import ApartmentQuerySet, Example
from example_project.app.types import ApartmentType
from query_optimizer import DjangoObjectType
from query_optimizer.typing import OptimizedDjangoOptions
from tests.factories import BuildingFactory


def test_object_type__no_model():
    with pytest.raises(TypeError, match="You need to pass a valid Django Model in FooType.Meta, received None."):

        class FooType(DjangoObjectType):
            class Meta:
                fields = "__all__"


def test_object_type__custom_options():
    class CustomOptions(OptimizedDjangoOptions):
        pass

    class CustomDjangoObjectType(DjangoObjectType):
        class Meta:
            abstract = True

        @classmethod
        def __init_subclass_with_meta__(cls, **options: Any) -> None:
            super().__init_subclass_with_meta__(_meta=CustomOptions(cls), **options)

    class ExampleType(CustomDjangoObjectType):
        class Meta:
            model = Example
            fields = "__all__"
            registry = Registry()

    assert isinstance(ExampleType._meta, CustomOptions)


def test_object_type__subscribed():
    class ExampleType(DjangoObjectType[Example]):
        class Meta:
            model = Example
            fields = "__all__"
            registry = Registry()

    assert ExampleType._meta.model is Example


@pytest.mark.django_db
def test_object_type__hooks_receive_default_manager_queryset(graphql_client):
    BuildingFactory.create(apartments__rooms=1)

    received: list[Any] = []

    def pre_optimization_hook(cls, queryset, optimizer):
        received.append(queryset)
        return queryset

    def filter_queryset(cls, queryset, info):
        received.append(queryset)
        return queryset

    query = """
        query {
          allBuildings {
            apartments {
              pk
            }
          }
        }
    """

    with (
        patch.object(ApartmentType, "pre_optimization_hook", classmethod(pre_optimization_hook)),
        patch.object(ApartmentType, "filter_queryset", classmethod(filter_queryset)),
    ):
        response = graphql_client(query)

    assert response.no_errors, response.errors

    assert len(received) == 2
    assert all(isinstance(queryset, ApartmentQuerySet) for queryset in received)
