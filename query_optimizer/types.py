from __future__ import annotations

from typing import TYPE_CHECKING

import graphene
import graphene_django
from django_filters.constants import ALL_FIELDS
from graphene_django.utils import is_valid_django_model

from . import optimize
from .settings import optimizer_settings
from .typing import PK, OptimizedDjangoOptions

if TYPE_CHECKING:
    from django.db.models import Model, QuerySet

    from .typing import Any, GQLInfo, Literal, Optional, TypeVar, Union

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
        model: Optional[type[Model]] = None,
        fields: Union[list[str], Literal["__all__"], None] = "__all__",
        max_complexity: Optional[int] = None,
        **options: Any,
    ) -> None:
        if not is_valid_django_model(model):
            msg = f"You need to pass a valid Django Model in {cls.__name__}.Meta, received {model}."
            raise TypeError(msg)

        if _meta is None:
            _meta = OptimizedDjangoOptions(cls)

        if not hasattr(cls, "pk") and (fields == ALL_FIELDS or "pk" in fields):
            cls.pk = graphene.Int() if model._meta.pk.name == "id" else graphene.ID()
            cls.resolve_pk = cls.resolve_id

        _meta.max_complexity = max_complexity or optimizer_settings.MAX_COMPLEXITY
        super().__init_subclass_with_meta__(_meta=_meta, model=model, fields=fields, **options)

    @classmethod
    def filter_queryset(cls, queryset: QuerySet[TModel], info: GQLInfo) -> QuerySet[TModel]:
        """Implement this method filter to the available rows from the model on this node."""
        return queryset

    @classmethod
    def get_queryset(cls, queryset: QuerySet[TModel], info: GQLInfo) -> QuerySet[TModel]:
        return queryset

    @classmethod
    def get_node(cls, info: GQLInfo, pk: PK) -> Optional[TModel]:
        queryset = cls._meta.model._default_manager.filter(pk=pk)
        queryset = optimize(queryset, info, max_complexity=cls._meta.max_complexity, pk=pk)
        # Shouldn't use .first(), as it can apply additional ordering, which would cancel the optimization.
        # The optimizer should have just inserted the right model instance based on the given primary key
        # to the queryset result cache anyway, so we can just pick that out. The only exception
        # is if the optimization was cancelled due to an error, and the result cache was not set,
        # in which case we fall back to .first().
        if queryset._result_cache is None:
            return queryset.first()  # pragma: no cover
        return queryset._result_cache[0]
