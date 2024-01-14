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
        """Implement this method filter to the available rows from the model on this node."""
        return queryset

    @classmethod
    def get_queryset(cls, queryset: QuerySet[TModel], info: GQLInfo) -> QuerySet[TModel]:
        if can_optimize(info):
            queryset = optimize(queryset, info, max_complexity=cls._meta.max_complexity)
        return queryset

    @classmethod
    def get_node(cls, info: GQLInfo, pk: PK) -> Optional[TModel]:
        queryset: QuerySet[TModel] = cls._meta.model.objects.filter(pk=pk)
        if can_optimize(info):
            queryset = optimize(queryset, info, max_complexity=cls._meta.max_complexity, pk=pk)
            # Can't use .first(), as it can apply additional ordering, which would cancel the optimization.
            # The optimizer should have just inserted the right model instance based on the given primary key
            # to the queryset result cache anyway, so we can just pick that out.
            return queryset._result_cache[0]
        return queryset.first()  # pragma: no cover
