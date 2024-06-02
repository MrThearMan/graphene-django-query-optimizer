from __future__ import annotations

from typing import TYPE_CHECKING

import graphene
from django.db import models
from graphene_django.converter import convert_django_field, get_django_field_description

from .settings import optimizer_settings

if TYPE_CHECKING:
    from graphene_django.registry import Registry

    from query_optimizer import DjangoObjectType
    from query_optimizer.fields import DjangoConnectionField, DjangoListField
    from query_optimizer.typing import Optional, Union

__all__ = [
    "convert_to_many_field",
    "convert_to_one_field",
]


@convert_django_field.register(models.OneToOneField)
@convert_django_field.register(models.ForeignKey)
@convert_django_field.register(models.OneToOneRel)
def convert_to_one_field(
    field,  # noqa: ANN001
    registry: Optional[Registry] = None,
) -> graphene.Dynamic:
    def dynamic_type() -> Optional[graphene.Field]:
        type_: Optional[type[DjangoObjectType]] = registry.get_type_for_model(field.related_model)
        if type_ is None:  # pragma: no cover
            return None

        actual_field = field.field if isinstance(field, models.OneToOneRel) else field
        description: str = get_django_field_description(actual_field)
        required: bool = False if isinstance(field, models.OneToOneRel) else not field.null

        from query_optimizer.fields import RelatedField

        return RelatedField(
            type_,
            description=description,
            required=required,
        )

    return graphene.Dynamic(dynamic_type)


@convert_django_field.register(models.ManyToManyField)
@convert_django_field.register(models.ManyToManyRel)
@convert_django_field.register(models.ManyToOneRel)
def convert_to_many_field(
    field,  # noqa: ANN001
    registry: Optional[Registry] = None,
) -> graphene.Dynamic:
    def dynamic_type() -> Union[DjangoConnectionField, DjangoListField, None]:
        type_: Optional[type[DjangoObjectType]] = registry.get_type_for_model(field.related_model)
        if type_ is None:  # pragma: no cover
            return None

        actual_field = field if isinstance(field, models.ManyToManyField) else field.field
        description: str = get_django_field_description(actual_field)
        required: bool = True  # will always return a queryset, even if empty

        from query_optimizer.fields import DjangoConnectionField, DjangoListField

        if type_._meta.connection and optimizer_settings.ALLOW_CONNECTION_AS_DEFAULT_NESTED_TO_MANY_FIELD:
            return DjangoConnectionField(  # pragma: no cover
                type_,
                required=required,
                description=description,
            )
        return DjangoListField(
            type_,
            required=required,
            description=description,
        )

    return graphene.Dynamic(dynamic_type)
