from __future__ import annotations

from typing import Any

import pytest
from graphene_django.registry import Registry

from example_project.app.models import Example
from query_optimizer import DjangoObjectType
from query_optimizer.typing import OptimizedDjangoOptions


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
