from __future__ import annotations

from typing import TYPE_CHECKING

import graphene
from django.db import models
from graphene.utils.str_converters import to_snake_case
from graphene_django import DjangoListField
from graphene_django.converter import convert_django_field, get_django_field_description

if TYPE_CHECKING:
    from graphene_django.registry import Registry

    from query_optimizer import DjangoObjectType
    from query_optimizer.fields import DjangoConnectionField
    from query_optimizer.typing import Any, GQLInfo, Optional, Union

__all__ = [
    "convert_reverse_to_one_field_to_django_model",
    "convert_forward_to_one_field_to_django_model",
    "convert_to_many_field_to_list_or_connection",
]


@convert_django_field.register(models.OneToOneRel)
def convert_reverse_to_one_field_to_django_model(
    field,  # noqa: ANN001
    registry: Optional[Registry] = None,
) -> graphene.Dynamic:
    def dynamic_type() -> Optional[graphene.Field]:
        _type: Optional[DjangoObjectType] = registry.get_type_for_model(field.related_model)
        if _type is None:  # pragma: no cover
            return None

        class CustomField(graphene.Field):
            def wrap_resolve(self, parent_resolver: Any) -> Any:
                def custom_resolver(root: Any, info: GQLInfo) -> Optional[models.Model]:
                    field_name = to_snake_case(info.field_name)
                    # Reverse object should be optimized to the root model.
                    reverse_object: Optional[models.Model] = getattr(root, field_name, None)
                    if reverse_object is None:  # pragma: no cover
                        return None

                    return _type.get_node(info, reverse_object.pk)

                return custom_resolver

        return CustomField(_type, description=get_django_field_description(field.field), required=not field.null)

    return graphene.Dynamic(dynamic_type)


@convert_django_field.register(models.OneToOneField)
@convert_django_field.register(models.ForeignKey)
def convert_forward_to_one_field_to_django_model(
    field,  # noqa: ANN001
    registry: Optional[Registry] = None,
) -> graphene.Dynamic:
    def dynamic_type() -> Optional[graphene.Field]:
        _type: Optional[DjangoObjectType] = registry.get_type_for_model(field.related_model)
        if _type is None:  # pragma: no cover
            return None

        class CustomField(graphene.Field):
            def wrap_resolve(self, parent_resolver: Any) -> Any:
                def custom_resolver(root: Any, info: GQLInfo) -> Optional[models.Model]:
                    field_name = to_snake_case(info.field_name)
                    db_field_key: str = root.__class__._meta.get_field(field_name).attname
                    object_pk = getattr(root, db_field_key, None)
                    if object_pk is None:  # pragma: no cover
                        return None

                    return _type.get_node(info, object_pk)

                return custom_resolver

        return CustomField(_type, description=get_django_field_description(field), required=not field.null)

    return graphene.Dynamic(dynamic_type)


@convert_django_field.register(models.ManyToManyField)
@convert_django_field.register(models.ManyToManyRel)
@convert_django_field.register(models.ManyToOneRel)
def convert_to_many_field_to_list_or_connection(
    field,  # noqa: ANN001
    registry: Optional[Registry] = None,
) -> graphene.Dynamic:
    def dynamic_type() -> Union[DjangoConnectionField, DjangoListField, None]:
        type_: Optional[type[DjangoObjectType]] = registry.get_type_for_model(field.related_model)
        if type_ is None:  # pragma: no cover
            return None

        description = get_django_field_description(field if isinstance(field, models.ManyToManyField) else field.field)

        if type_._meta.connection:  # pragma: no cover
            from query_optimizer.fields import DjangoConnectionField

            return DjangoConnectionField(type_, required=True, description=description)
        return DjangoListField(type_, required=True, description=description)

    return graphene.Dynamic(dynamic_type)
