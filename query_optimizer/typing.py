from __future__ import annotations

from typing import (
    TYPE_CHECKING,
    Any,
    Callable,
    Collection,
    Generator,
    Hashable,
    Iterable,
    Literal,
    NamedTuple,
    Optional,
    Type,
    TypedDict,
    TypeVar,
    Union,
)

from graphene.relay.connection import ConnectionOptions
from graphene_django.types import DjangoObjectTypeOptions
from graphql_relay import ConnectionType

# New in version 3.10
try:
    from typing import ParamSpec, TypeAlias, TypeGuard
except ImportError:
    from typing_extensions import ParamSpec, TypeAlias, TypeGuard


from django.core.handlers.wsgi import WSGIRequest
from django.db.models import (
    Field,
    ForeignKey,
    ForeignObject,
    ForeignObjectRel,
    Manager,
    ManyToManyField,
    ManyToManyRel,
    ManyToOneRel,
    Model,
    OneToOneField,
    QuerySet,
)
from graphql import GraphQLResolveInfo

if TYPE_CHECKING:
    from django.contrib.auth.models import AnonymousUser, User
    from django.contrib.contenttypes.fields import GenericForeignKey, GenericRelation

__all__ = [
    "Any",
    "Callable",
    "Collection",
    "ConnectionResolver",
    "GQLInfo",
    "Generator",
    "Hashable",
    "Iterable",
    "Literal",
    "ModelField",
    "NamedTuple",
    "OptimizedDjangoOptions",
    "Optional",
    "PK",
    "ParamSpec",
    "QueryCache",
    "QuerySetResolver",
    "StoreStr",
    "TableName",
    "ToManyField",
    "ToOneField",
    "Type",
    "TypeGuard",
    "TypeOptions",
    "TypeVar",
    "TypedDict",
    "Union",
]


TModel = TypeVar("TModel", bound=Model)
TableName: TypeAlias = str
StoreStr: TypeAlias = str
PK: TypeAlias = Any
QueryCache: TypeAlias = dict[TableName, dict[StoreStr, dict[PK, TModel]]]
ModelField: TypeAlias = Union[Field, ForeignObjectRel, "GenericForeignKey"]
ToManyField: TypeAlias = Union["GenericRelation", ManyToManyField, ManyToOneRel, ManyToManyRel]
ToOneField: TypeAlias = Union["GenericRelation", ForeignObject, ForeignKey, OneToOneField]
TypeOptions: TypeAlias = Union[DjangoObjectTypeOptions, ConnectionOptions]
AnyUser: TypeAlias = Union["User", "AnonymousUser"]

QuerySetResolver = Callable[..., Union[QuerySet, Manager, None]]
ConnectionResolver = Callable[..., ConnectionType]


class UserHintedWSGIRequest(WSGIRequest):
    user: AnyUser


class GQLInfo(GraphQLResolveInfo):
    context: UserHintedWSGIRequest


class OptimizedDjangoOptions(DjangoObjectTypeOptions):
    max_complexity: int
