from typing import Any, Callable, Hashable, Iterable, TypeVar, Union

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
    "Callable",
    "GQLInfo",
    "Hashable",
    "Iterable",
    "ModelField",
    "PK_CACHE_KEY",
    "QueryCache",
    "TypeGuard",
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

PK_CACHE_KEY = "_query_optimizer_model_pk"
