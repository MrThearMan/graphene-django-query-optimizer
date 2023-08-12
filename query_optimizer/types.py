import graphene_django
from django.db.models import Model, QuerySet
from graphene.relay.connection import Connection
from graphene.types.definitions import GrapheneObjectType
from graphql.type.definition import GraphQLNonNull

from .optimizer import optimize
from .typing import PK, PK_CACHE_KEY, GQLInfo, TypeVar, Union

TModel = TypeVar("TModel", bound=Model)


__all__ = [
    "DjangoObjectType",
]


class DjangoObjectType(graphene_django.types.DjangoObjectType):
    class Meta:
        abstract = True

    @classmethod
    def can_optimize_resolver(cls, info: GQLInfo) -> bool:
        return_type = info.return_type
        if isinstance(return_type, GraphQLNonNull):
            return_type = return_type.of_type

        return isinstance(return_type, GrapheneObjectType) and (
            issubclass(return_type.graphene_type, (cls, Connection))
        )

    @classmethod
    def get_queryset(cls, queryset: QuerySet[TModel], info: GQLInfo) -> QuerySet[TModel]:
        if cls.can_optimize_resolver(info):
            queryset = optimize(queryset, info)
        return queryset

    @classmethod
    def get_node(cls, info: GQLInfo, id: PK) -> Union[TModel, None]:  # noqa: A002
        queryset: QuerySet[TModel] = cls._meta.model.objects.all()
        setattr(queryset, PK_CACHE_KEY, id)
        queryset = cls.get_queryset(queryset, info)
        return queryset.first()
