from __future__ import annotations

from typing import TYPE_CHECKING

import graphene
import graphene_django
from django_filters.constants import ALL_FIELDS
from graphene_django.utils import is_valid_django_model

from .compiler import optimize_single
from .settings import optimizer_settings
from .typing import PK, OptimizedDjangoOptions

if TYPE_CHECKING:
    from django.db.models import Model, QuerySet

    from .optimizer import QueryOptimizer
    from .typing import Any, GQLInfo, Literal, Optional, TModel, Union


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
        if not is_valid_django_model(model):  # pragma: no cover
            msg = f"You need to pass a valid Django Model in {cls.__name__}.Meta, received {model}."
            raise TypeError(msg)

        if _meta is None:
            _meta = OptimizedDjangoOptions(cls)

        if not hasattr(cls, "pk") and (fields == ALL_FIELDS or "pk" in fields):
            cls.pk = graphene.Int() if model._meta.pk.name == "id" else graphene.ID()
            cls.resolve_pk = cls.resolve_id

        filterset_class = options.get("filterset_class", None)
        filter_fields: Optional[dict[str, list[str]]] = options.pop("filter_fields", None)

        if filterset_class is None and filter_fields is not None:
            from .filter import create_filterset

            options["filterset_class"] = create_filterset(model, filter_fields)

        _meta.max_complexity = max_complexity or optimizer_settings.MAX_COMPLEXITY
        super().__init_subclass_with_meta__(_meta=_meta, model=model, fields=fields, **options)

    @classmethod
    def pre_optimization_hook(cls, queryset: QuerySet[TModel], optimizer: QueryOptimizer) -> QuerySet[TModel]:
        """A hook for modifying the optimizer results before optimization happens."""
        return queryset

    @classmethod
    def filter_queryset(cls, queryset: QuerySet[TModel], info: GQLInfo) -> QuerySet[TModel]:
        """Implement this method filter to the available rows from the model on this node."""
        return queryset

    @classmethod
    def get_queryset(cls, queryset: QuerySet[TModel], info: GQLInfo) -> QuerySet[TModel]:
        return queryset

    @classmethod
    def get_node(cls, info: GQLInfo, pk: PK) -> Optional[TModel]:
        queryset = cls._meta.model._default_manager.all()
        maybe_instance = optimize_single(queryset, info, pk=pk, max_complexity=cls._meta.max_complexity)
        if maybe_instance is not None:  # pragma: no cover
            cls.run_instance_checks(maybe_instance, info)
        return maybe_instance

    @classmethod
    def run_instance_checks(cls, instance: TModel, info: GQLInfo) -> None:
        """A hook for running checks after getting a single instance."""
