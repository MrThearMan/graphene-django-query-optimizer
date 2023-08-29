from typing import Any, Callable, Collection, Hashable, Iterable, NamedTuple, Optional, TypeVar, Union

from graphene.relay.connection import ConnectionOptions
from graphene_django.types import DjangoObjectTypeOptions

# New in version 3.10
try:
    from typing import TypeAlias, TypeGuard
except ImportError:
    from typing_extensions import TypeAlias, TypeGuard


import graphql
from django.contrib.contenttypes.fields import GenericForeignKey, GenericRelation
from django.core.handlers.wsgi import WSGIRequest
from django.db.models import (
    Field,
    ForeignKey,
    ForeignObject,
    ForeignObjectRel,
    ManyToManyField,
    ManyToManyRel,
    ManyToOneRel,
    Model,
    OneToOneField,
)

__all__ = [
    "Any",
    "Callable",
    "Collection",
    "GQLInfo",
    "Hashable",
    "Iterable",
    "ModelField",
    "NamedTuple",
    "Optional",
    "PK",
    "QueryCache",
    "StoreStr",
    "TableName",
    "ToManyField",
    "ToOneField",
    "TypeGuard",
    "TypeOptions",
    "TypeVar",
    "Union",
]


class GQLInfo(graphql.GraphQLResolveInfo):
    context: WSGIRequest


TModel = TypeVar("TModel", bound=Model)
TableName: TypeAlias = str
StoreStr: TypeAlias = str
PK: TypeAlias = Any
QueryCache: TypeAlias = dict[TableName, dict[StoreStr, dict[PK, TModel]]]
ModelField: TypeAlias = Union[Field, ForeignObjectRel, GenericForeignKey]
ToManyField: TypeAlias = Union[GenericRelation, ManyToManyField, ManyToOneRel, ManyToManyRel]
ToOneField: TypeAlias = Union[GenericRelation, ForeignObject, ForeignKey, OneToOneField]
TypeOptions: TypeAlias = Union[DjangoObjectTypeOptions, ConnectionOptions]
