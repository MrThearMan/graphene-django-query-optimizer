from __future__ import annotations

from unittest.mock import Mock

from graphene_django.registry import Registry

from example_project.app.models import Apartment, HousingCompany
from example_project.app.types import HousingCompanyNode
from query_optimizer.converters import convert_to_many_field, convert_to_one_field
from query_optimizer.fields import DjangoConnectionField


def test_convert_to_one_field__related_model_not_registered():
    field = Apartment._meta.get_field("building")

    dynamic = convert_to_one_field(field, registry=Registry())

    assert dynamic.get_type() is None


def test_convert_to_many_field__related_model_not_registered():
    field = HousingCompany._meta.get_field("developers")

    dynamic = convert_to_many_field(field, registry=Registry())

    assert dynamic.get_type() is None


def test_convert_to_many_field__connection(settings):
    settings.GRAPHQL_QUERY_OPTIMIZER = {"ALLOW_CONNECTION_AS_DEFAULT_NESTED_TO_MANY_FIELD": True}
    field = HousingCompany._meta.get_field("developers")
    registry = Mock()
    registry.get_type_for_model.return_value = HousingCompanyNode

    dynamic = convert_to_many_field(field, registry=registry)

    assert isinstance(dynamic.get_type(), DjangoConnectionField)
