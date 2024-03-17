from __future__ import annotations

from typing import (
    TYPE_CHECKING,
    Any,
    Callable,
    Collection,
    ContextManager,
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
    cast,
    overload,
)

from django.db import models
from graphene.relay.connection import ConnectionOptions
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
from graphql import FieldNode, GraphQLResolveInfo, SelectionNode

if TYPE_CHECKING:
    from django.contrib.auth.models import AnonymousUser, User
    from django.contrib.contenttypes.fields import GenericForeignKey, GenericRelation
    from django_filters import FilterSet

__all__ = [
    "Any",
    "Callable",
    "Collection",
    "ConnectionResolver",
    "ContextManager",
    "Expr",
    "FieldNodes",
    "FilterFields",
    "GQLInfo",
    "GRAPHQL_BUILTIN",
    "Generator",
    "GraphQLFilterInfo",
    "Hashable",
    "Iterable",
    "Literal",
    "ModelField",
    "ModelResolver",
    "NamedTuple",
    "ObjectTypeInput",
    "OptimizedDjangoOptions",
    "OptimizerKey",
    "Optional",
    "PK",
    "ParamSpec",
    "QueryCache",
    "QuerySetResolver",
    "TableName",
    "ToManyField",
    "ToOneField",
    "Type",
    "TypeGuard",
    "TypeOptions",
    "TypeVar",
    "TypedDict",
    "Union",
    "UnmountedTypeInput",
    "cast",
    "overload",
]


TModel = TypeVar("TModel", bound=Model)
TableName: TypeAlias = str
OptimizerKey: TypeAlias = str
PK: TypeAlias = Any
QueryCache: TypeAlias = dict[TableName, dict[OptimizerKey, dict[PK, TModel]]]
ModelField: TypeAlias = Union[Field, ForeignObjectRel, "GenericForeignKey"]
ToManyField: TypeAlias = Union["GenericRelation", ManyToManyField, ManyToOneRel, ManyToManyRel]
ToOneField: TypeAlias = Union["GenericRelation", ForeignObject, ForeignKey, OneToOneField]
TypeOptions: TypeAlias = Union[DjangoObjectTypeOptions, ConnectionOptions]
AnyUser: TypeAlias = Union["User", "AnonymousUser"]
FilterFields: TypeAlias = Union[dict[str, list[str]], list[str]]
QuerySetResolver: TypeAlias = Callable[..., Union[QuerySet, Manager, None]]
ModelResolver: TypeAlias = Callable[..., Union[Model, None]]
ConnectionResolver: TypeAlias = Callable[..., ConnectionType]
FieldNodes: TypeAlias = Iterable[Union[FieldNode, SelectionNode]]
ObjectTypeInput: TypeAlias = Union[type[DjangoObjectType], str, Callable[[], type[DjangoObjectType]]]
UnmountedTypeInput: TypeAlias = Union[type[UnmountedType], str, Callable[[], type[UnmountedType]]]
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
