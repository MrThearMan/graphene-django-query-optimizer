from typing import Any

import graphene_django
from django.db.models import QuerySet
from graphene.types.definitions import GrapheneObjectType
from graphql import GraphQLNonNull

from .optimizer import optimize
from .typing import GQLInfo, TModel


class DjangoObjectType(graphene_django.types.DjangoObjectType):
    class Meta:
        abstract = True

    @classmethod
    def can_optimize_resolver(cls, info: GQLInfo) -> bool:
        return_type = info.return_type
        if isinstance(return_type, GraphQLNonNull):
            return_type = return_type.of_type

        return isinstance(return_type, GrapheneObjectType) and return_type.graphene_type is cls

    @classmethod
    def get_queryset(cls, queryset: QuerySet[TModel], info: GQLInfo) -> QuerySet[TModel]:
        if cls.can_optimize_resolver(info):
            queryset = optimize(queryset, info)
        return queryset

    @classmethod
    def get_node(cls, info: GQLInfo, id: Any) -> TModel | None:
        queryset: QuerySet[TModel] = cls._meta.model.objects.all()
        queryset._cached_model_pk = id
        queryset = cls.get_queryset(queryset, info)
        return queryset.first()
