from __future__ import annotations

from typing import TYPE_CHECKING

import graphene_django

from .optimizer import optimize
from .settings import optimizer_settings
from .typing import OptimizedDjangoOptions
from .utils import can_optimize

if TYPE_CHECKING:
    from django.db.models import Model, QuerySet

    from .typing import PK, Any, GQLInfo, Optional, TypeVar

    TModel = TypeVar("TModel", bound=Model)


__all__ = [
    "DjangoObjectType",
]


class DjangoObjectType(graphene_django.types.DjangoObjectType):
    """DjangoObjectType that automatically optimizes its queryset."""

    _meta: OptimizedDjangoOptions

    class Meta:
        abstract = True

    @classmethod
    def __init_subclass_with_meta__(
        cls,
        _meta: Optional[OptimizedDjangoOptions] = None,
        max_complexity: int | None = None,
        **options: Any,
    ) -> None:
        if _meta is None:
            _meta = OptimizedDjangoOptions(cls)

        _meta.max_complexity = max_complexity or optimizer_settings.MAX_COMPLEXITY
        super().__init_subclass_with_meta__(_meta=_meta, **options)

    @classmethod
    def filter_queryset(cls, queryset: QuerySet[TModel], info: GQLInfo) -> QuerySet[TModel]:
        """override this method to"""
        return queryset

    @classmethod
    def get_queryset(cls, queryset: QuerySet[TModel], info: GQLInfo) -> QuerySet[TModel]:
        if can_optimize(info):
            queryset = optimize(queryset, info, max_complexity=cls._meta.max_complexity)
        return queryset

    @classmethod
    def get_node(cls, info: GQLInfo, id: PK) -> Optional[TModel]:  # noqa: A002
        queryset: QuerySet[TModel] = cls._meta.model.objects.filter(pk=id)
        if can_optimize(info):
            queryset = optimize(queryset, info, max_complexity=cls._meta.max_complexity, pk=id)
        return queryset.first()
