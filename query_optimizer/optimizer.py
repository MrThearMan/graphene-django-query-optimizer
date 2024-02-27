from __future__ import annotations

import dataclasses
from typing import TYPE_CHECKING

from django.core.exceptions import ValidationError
from django.db.models import Expression, Model, Prefetch, QuerySet
from django.db.models.constants import LOOKUP_SEP
from graphene_django.registry import get_global_registry

from .settings import optimizer_settings
from .utils import get_filter_info, mark_optimized

if TYPE_CHECKING:
    from .types import DjangoObjectType
    from .typing import Any, GQLInfo, GraphQLFilterInfo, Optional, TypeVar

    TModel = TypeVar("TModel", bound=Model)


__all__ = [
    "QueryOptimizer",
]


@dataclasses.dataclass
class CompilationResults:
    only_fields: list[str] = dataclasses.field(default_factory=list)
    select_related: list[str] = dataclasses.field(default_factory=list)
    prefetch_related: list[Prefetch] = dataclasses.field(default_factory=list)


class QueryOptimizer:
    """Creates optimized queryset based on the optimization data found by the OptimizationCompiler."""

    def __init__(self, model: type[Model], info: GQLInfo) -> None:
        self.model = model
        self.info = info
        self.only_fields: list[str] = []
        self.related_fields: list[str] = []
        self.annotations: dict[str, Expression] = {}
        self.select_related: dict[str, QueryOptimizer] = {}
        self.prefetch_related: dict[str, QueryOptimizer] = {}

    def optimize_queryset(
        self,
        queryset: QuerySet[TModel],
        *,
        filter_info: Optional[GraphQLFilterInfo] = None,
    ) -> QuerySet[TModel]:
        """
        Add the optimizations in this optimizer to the given queryset.

        :param queryset: QuerySet to optimize.
        :param filter_info: Additional filtering info to use for the optimization.
        """
        if filter_info is None:
            filter_info = get_filter_info(self.info)

        results = self.compile(filter_info=filter_info)

        queryset = self.get_filtered_queryset(queryset)

        if filter_info is not None and filter_info.get("filterset_class") is not None:
            filterset = filter_info["filterset_class"](
                data=self.process_filters(filter_info["filters"]),
                queryset=queryset,
                request=self.info.context,
            )
            if not filterset.is_valid():  # pragma: no cover
                raise ValidationError(filterset.form.errors.as_json())

            queryset = filterset.qs

        if results.prefetch_related:
            queryset = queryset.prefetch_related(*results.prefetch_related)
        if results.select_related:
            queryset = queryset.select_related(*results.select_related)
        if not optimizer_settings.DISABLE_ONLY_FIELDS_OPTIMIZATION and (results.only_fields or self.related_fields):
            queryset = queryset.only(*results.only_fields, *self.related_fields)
        if self.annotations:
            queryset = queryset.annotate(**self.annotations)

        mark_optimized(queryset)
        return queryset

    def compile(self, *, filter_info: GraphQLFilterInfo) -> CompilationResults:
        results = CompilationResults(only_fields=self.only_fields.copy())

        for name, optimizer in self.select_related.items():
            # Promote select related to prefetch related if any annotations are needed.
            if optimizer.annotations:
                self.compile_prefetch(name, optimizer, results, filter_info)
            else:
                self.compile_select(name, optimizer, results, filter_info)

        for name, optimizer in self.prefetch_related.items():
            self.compile_prefetch(name, optimizer, results, filter_info)

        return results

    def compile_select(
        self,
        name: str,
        optimizer: QueryOptimizer,
        results: CompilationResults,
        filter_info: GraphQLFilterInfo,
    ) -> None:
        results.select_related.append(name)
        nested_results = optimizer.compile(filter_info=filter_info)
        results.only_fields.extend(f"{name}{LOOKUP_SEP}{only}" for only in nested_results.only_fields)
        results.select_related.extend(f"{name}{LOOKUP_SEP}{select}" for select in nested_results.select_related)
        for prefetch in nested_results.prefetch_related:
            prefetch.add_prefix(name)
            results.prefetch_related.append(prefetch)

    def compile_prefetch(
        self,
        name: str,
        optimizer: QueryOptimizer,
        results: CompilationResults,
        filter_info: GraphQLFilterInfo,
    ) -> None:
        queryset = self.get_prefetch_queryset(optimizer.model)
        filter_info = filter_info.get("children", {}).get(name, {})
        optimized_queryset = optimizer.optimize_queryset(queryset, filter_info=filter_info)
        results.prefetch_related.append(Prefetch(name, optimized_queryset))

    def get_prefetch_queryset(self, model: type[TModel]) -> QuerySet[TModel]:
        return model._default_manager.all()

    def get_filtered_queryset(self, queryset: QuerySet[TModel]) -> QuerySet[TModel]:
        object_type: Optional[DjangoObjectType] = get_global_registry().get_type_for_model(queryset.model)
        if callable(getattr(object_type, "filter_queryset", None)):
            return object_type.filter_queryset(queryset, self.info)  # type: ignore[union-attr]
        return queryset  # pragma: no cover

    def process_filters(self, input_data: dict[str, Any]) -> dict[str, Any]:
        from graphene_django.filter.fields import convert_enum

        return {key: convert_enum(value) for key, value in input_data.items()}

    def __add__(self, other: QueryOptimizer) -> QueryOptimizer:
        self.only_fields += other.only_fields
        self.related_fields += other.related_fields
        self.annotations.update(other.annotations)
        self.select_related.update(other.select_related)
        self.prefetch_related.update(other.prefetch_related)
        return self

    def __str__(self) -> str:
        filter_info = get_filter_info(self.info)
        results = self.compile(filter_info=filter_info)
        only = ",".join(results.only_fields)
        select = ",".join(results.select_related)
        prefetch = ",".join(item.prefetch_to for item in results.prefetch_related)
        return f"{only=}|{select=}|{prefetch=}"
