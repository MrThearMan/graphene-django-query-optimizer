import graphene_django
from django.db.models import Model, QuerySet

from .optimizer import optimize
from .settings import optimizer_settings
from .typing import PK, GQLInfo, Optional, TypeVar
from .utils import can_optimize

TModel = TypeVar("TModel", bound=Model)


__all__ = [
    "DjangoObjectType",
]


class DjangoObjectType(graphene_django.types.DjangoObjectType):
    """DjangoObjectType that automatically optimizes its queryset."""

    class Meta:
        abstract = True

    @classmethod
    def max_complexity(cls) -> int:
        return optimizer_settings.MAX_COMPLEXITY  # type: ignore[no-any-return]

    @classmethod
    def get_queryset(cls, queryset: QuerySet[TModel], info: GQLInfo) -> QuerySet[TModel]:
        if can_optimize(info):
            queryset = optimize(queryset, info, max_complexity=cls.max_complexity())
        return queryset

    @classmethod
    def get_node(cls, info: GQLInfo, id: PK) -> Optional[TModel]:  # noqa: A002
        queryset: QuerySet[TModel] = cls._meta.model.objects.filter(pk=id)
        if can_optimize(info):
            queryset = optimize(queryset, info, max_complexity=cls.max_complexity(), pk=id)
        return queryset.first()
