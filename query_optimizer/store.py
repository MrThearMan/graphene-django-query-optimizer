from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from django.db.models import Model, Prefetch, QuerySet
from django.db.models.constants import LOOKUP_SEP

from .settings import optimizer_settings
from .utils import mark_optimized, unique

if TYPE_CHECKING:
    from .typing import PK, TypeVar

    TModel = TypeVar("TModel", bound=Model)


__all__ = [
    "QueryOptimizerStore",
]


@dataclass
class CompilationResults:
    only_fields: list[str]
    related_fields: list[str]
    select_related: list[str]
    prefetch_related: list[Prefetch]


class QueryOptimizerStore:
    """Store for holding optimization data."""

    def __init__(self, model: type[Model]) -> None:
        self.model = model
        self.only_fields: list[str] = []
        self.related_fields: list[str] = []
        self.select_stores: dict[str, QueryOptimizerStore] = {}
        self.prefetch_stores: dict[str, tuple[QueryOptimizerStore, QuerySet[Model]]] = {}

    def compile(self, *, in_prefetch: bool = False) -> CompilationResults:  # noqa: A003
        results = CompilationResults(
            only_fields=self.only_fields.copy(),
            related_fields=self.related_fields.copy(),
            select_related=[],
            prefetch_related=[],
        )

        for name, store in self.select_stores.items():
            if not in_prefetch:
                results.select_related.append(name)
            self._compile_nested(name, store, results, in_prefetch=in_prefetch)

        for name, (store, queryset) in self.prefetch_stores.items():
            optimized_queryset = store.optimize_queryset(queryset)
            results.prefetch_related.append(Prefetch(name, optimized_queryset))
            self._compile_nested(name, store, results, in_prefetch=True)

        results.only_fields = unique(results.only_fields)
        results.related_fields = unique(results.related_fields)
        results.select_related = unique(results.select_related)
        results.prefetch_related = unique(results.prefetch_related)
        return results

    @staticmethod
    def _compile_nested(
        name: str,
        store: QueryOptimizerStore,
        results: CompilationResults,
        *,
        in_prefetch: bool,
    ) -> None:
        nested_results = store.compile(in_prefetch=in_prefetch)
        if not in_prefetch:
            results.only_fields.extend(f"{name}{LOOKUP_SEP}{only}" for only in nested_results.only_fields)

        results.select_related.extend(f"{name}{LOOKUP_SEP}{select}" for select in nested_results.select_related)
        for prefetch in nested_results.prefetch_related:
            prefetch.add_prefix(name)
            results.prefetch_related.append(prefetch)

    def optimize_queryset(
        self,
        queryset: QuerySet[TModel],
        *,
        pk: PK = None,
    ) -> QuerySet[TModel]:
        results = self.compile()

        if results.prefetch_related:
            queryset = queryset.prefetch_related(*results.prefetch_related)
        if results.select_related:
            queryset = queryset.select_related(*results.select_related)
        if not optimizer_settings.DISABLE_ONLY_FIELDS_OPTIMIZATION and (results.only_fields or results.related_fields):
            queryset = queryset.only(*results.only_fields, *results.related_fields)
        if pk is not None:
            queryset = queryset.filter(pk=pk)

        mark_optimized(queryset)
        return queryset

    @property
    def complexity(self) -> int:
        value: int = 0
        for store in self.select_stores.values():
            value += store.complexity
        for store, _ in self.prefetch_stores.values():
            value += store.complexity
        return value + len(self.select_stores) + len(self.prefetch_stores)

    def __add__(self, other: QueryOptimizerStore) -> QueryOptimizerStore:
        self.only_fields += other.only_fields
        self.related_fields += other.related_fields
        self.select_stores.update(other.select_stores)
        self.prefetch_stores.update(other.prefetch_stores)
        return self

    def __str__(self) -> str:
        results = self.compile()
        only = ",".join(results.only_fields)
        select = ",".join(results.select_related)
        prefetch = ",".join(item.prefetch_to for item in results.prefetch_related)
        return f"{only=}|{select=}|{prefetch=}"
