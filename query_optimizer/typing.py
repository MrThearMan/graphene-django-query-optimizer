from __future__ import annotations

from typing import (
    TYPE_CHECKING,
    Any,
    Callable,
    Collection,
    Hashable,
    Iterable,
    Literal,
    NamedTuple,
    Optional,
    TypeVar,
    Union,
)

from graphene.relay.connection import ConnectionOptions
from graphene_django.types import DjangoObjectTypeOptions

# New in version 3.10
try:
    from typing import TypeAlias, TypeGuard
except ImportError:
    from typing_extensions import TypeAlias, TypeGuard


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
from graphql import GraphQLResolveInfo

if TYPE_CHECKING:
    from django.contrib.auth.models import AnonymousUser, User

__all__ = [
    "Any",
    "Callable",
    "Collection",
    "GQLInfo",
    "Hashable",
    "Iterable",
    "Literal",
    "ModelField",
    "NamedTuple",
    "OptimizedDjangoOptions",
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


TModel = TypeVar("TModel", bound=Model)
TableName: TypeAlias = str
StoreStr: TypeAlias = str
PK: TypeAlias = Any
QueryCache: TypeAlias = dict[TableName, dict[StoreStr, dict[PK, TModel]]]
ModelField: TypeAlias = Union[Field, ForeignObjectRel, GenericForeignKey]
ToManyField: TypeAlias = Union[GenericRelation, ManyToManyField, ManyToOneRel, ManyToManyRel]
ToOneField: TypeAlias = Union[GenericRelation, ForeignObject, ForeignKey, OneToOneField]
TypeOptions: TypeAlias = Union[DjangoObjectTypeOptions, ConnectionOptions]
AnyUser: TypeAlias = Union["User", "AnonymousUser"]


class UserHintedWSGIRequest(WSGIRequest):
    user: AnyUser


class GQLInfo(GraphQLResolveInfo):
    context: UserHintedWSGIRequest


class OptimizedDjangoOptions(DjangoObjectTypeOptions):
    max_complexity: int
