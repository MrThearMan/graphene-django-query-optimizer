from django.db.models import Field, ForeignKey
from graphene.types.definitions import GrapheneObjectType
from graphql import GraphQLOutputType

__all__ = [
    "is_foreign_key_id",
    "get_base_object_type",
]


def is_foreign_key_id(model_field: Field, name: str) -> bool:
    return isinstance(model_field, ForeignKey) and model_field.name != name and model_field.get_attname() == name


def get_base_object_type(field_type: GraphQLOutputType) -> GrapheneObjectType:
    while hasattr(field_type, "of_type"):
        field_type = field_type.of_type
    return field_type
