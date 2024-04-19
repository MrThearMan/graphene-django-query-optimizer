from __future__ import annotations

from typing import (
    TYPE_CHECKING,
    Any,
    Callable,
    Collection,
    ContextManager,
    Generator,
    Generic,
    Hashable,
    Iterable,
    Literal,
    NamedTuple,
    Optional,
    Protocol,
    Type,
    TypedDict,
    TypeVar,
    Union,
    cast,
    overload,
)

from django.db import models
from graphene import Argument, Dynamic
from graphene.types.structures import Structure
from graphene.types.unmountedtype import UnmountedType
from graphene_django import DjangoObjectType
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
    from django.db.models.sql import Query
    from django_filters import FilterSet

__all__ = [
    "Any",
    "ArgTypeInput",
    "Callable",
    "cast",
    "Collection",
    "ConnectionResolver",
    "ContextManager",
    "Expr",
    "ExpressionKind",
    "Generator",
    "Generic",
    "GQLInfo",
    "GRAPHQL_BUILTIN",
    "GraphQLFilterInfo",
    "Hashable",
    "Iterable",
    "Literal",
    "ModelField",
    "ModelResolver",
    "NamedTuple",
    "ObjectTypeInput",
    "OptimizedDjangoOptions",
    "Optional",
    "overload",
    "ParamSpec",
    "PK",
    "QuerySetResolver",
    "ToManyField",
    "ToOneField",
    "Type",
    "TypedDict",
    "TypeGuard",
    "TypeVar",
    "Union",
    "UnmountedTypeInput",
]


TModel = TypeVar("TModel", bound=Model)
PK: TypeAlias = Any
ModelField: TypeAlias = Union[Field, ForeignObjectRel, "GenericForeignKey"]
ToManyField: TypeAlias = Union["GenericRelation", ManyToManyField, ManyToOneRel, ManyToManyRel]
ToOneField: TypeAlias = Union["GenericRelation", ForeignObject, ForeignKey, OneToOneField]
AnyUser: TypeAlias = Union["User", "AnonymousUser"]
QuerySetResolver: TypeAlias = Callable[..., Union[QuerySet, Manager, None]]
ModelResolver: TypeAlias = Callable[..., Union[Model, None]]
ConnectionResolver: TypeAlias = Callable[..., ConnectionType]
ObjectTypeInput: TypeAlias = Union[str, type[DjangoObjectType], Callable[[], type[DjangoObjectType]]]
UnmountedTypeInput: TypeAlias = Union[str, type[UnmountedType], Structure, Callable[[], type[UnmountedType]]]
ArgTypeInput: TypeAlias = Union[Argument, UnmountedType, Dynamic]
Expr: TypeAlias = Union[models.Expression, models.F, models.Q]


GRAPHQL_BUILTIN = (
    "__typename",
    "__schema",
    "__type",
    "__typekind",
    "__field",
    "__inputvalue",
    "__enumvalue",
    "__directive",
)


class UserHintedWSGIRequest(WSGIRequest):
    user: AnyUser


class GQLInfo(GraphQLResolveInfo):
    context: UserHintedWSGIRequest


class OptimizedDjangoOptions(DjangoObjectTypeOptions):
    max_complexity: int


class GraphQLFilterInfo(TypedDict, total=False):
    name: str
    filters: dict[str, Any]
    children: dict[str, GraphQLFilterInfo]
    filterset_class: Optional[type[FilterSet]]
    is_connection: bool
    is_node: bool
    max_limit: Optional[int]


class ExpressionKind(Protocol):
    def resolve_expression(
        self,
        query: Query,
        allow_joins: bool,  # noqa: FBT001
        reuse: set[str] | None,
        summarize: bool,  # noqa: FBT001
        for_save: bool,  # noqa: FBT001
    ) -> ExpressionKind: ...
