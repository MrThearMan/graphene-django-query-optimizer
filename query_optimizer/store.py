from django.db.models import Model, Prefetch, QuerySet
from django.db.models.constants import LOOKUP_SEP

from .typing import PK, TypeVar

TModel = TypeVar("TModel", bound=Model)


__all__ = [
    "QueryOptimizerStore",
]


class QueryOptimizerStore:
    def __init__(self) -> None:
        self.only_fields: list[str] = []
        self.select_stores: dict[str, "QueryOptimizerStore"] = {}
        self.prefetch_stores: dict[str, tuple["QueryOptimizerStore", QuerySet[Model]]] = {}

    def only(self, field: str) -> None:
        self.only_fields.append(field)

    def select_related(self, name: str, store: "QueryOptimizerStore") -> None:
        self.select_stores[name] = store

    def prefetch_related(self, name: str, store: "QueryOptimizerStore", queryset: QuerySet[Model]) -> None:
        self.prefetch_stores[name] = (store, queryset)

    def compile(self, *, in_prefetch: bool = False) -> tuple[list[str], list[str], list[Prefetch]]:  # noqa: A003
        only_fields: list[str] = self.only_fields.copy()
        select_related: list[str] = []
        prefetch_related: list[Prefetch] = []

        for name, store in self.select_stores.items():
            if not in_prefetch:
                select_related.append(name)
            self._compile_nested(store, name, only_fields, select_related, prefetch_related, in_prefetch=in_prefetch)

        for name, (store, queryset) in self.prefetch_stores.items():
            optimized_queryset = store.optimize_queryset(queryset)
            prefetch_related.append(Prefetch(name, optimized_queryset))
            self._compile_nested(store, name, only_fields, select_related, prefetch_related, in_prefetch=True)

        return only_fields, select_related, prefetch_related

    @staticmethod
    def _compile_nested(
        store: "QueryOptimizerStore",
        name: str,
        only_fields: list[str],
        select_related: list[str],
        prefetch_related: list[Prefetch],
        *,
        in_prefetch: bool,
    ) -> None:
        store_only_list, store_select_related, store_prefetch_related = store.compile(in_prefetch=in_prefetch)
        if not in_prefetch:
            only_fields.extend(name + LOOKUP_SEP + only for only in store_only_list)
        select_related.extend(name + LOOKUP_SEP + select for select in store_select_related)
        for prefetch in store_prefetch_related:
            prefetch.add_prefix(name)
            prefetch_related.append(prefetch)

    def optimize_queryset(self, queryset: QuerySet[TModel], *, pk: PK = None) -> QuerySet[TModel]:
        only_fields, select_related, prefetch_related = self.compile()

        if only_fields:
            queryset = queryset.only(*only_fields)
        if select_related:
            queryset = queryset.select_related(*select_related)
        if prefetch_related:
            queryset = queryset.prefetch_related(*prefetch_related)
        if pk is not None:
            queryset = queryset.filter(pk=pk)

        return queryset

    def __add__(self, other: "QueryOptimizerStore") -> "QueryOptimizerStore":
        self.only_fields += other.only_fields
        self.select_stores.update(other.select_stores)
        self.prefetch_stores.update(other.prefetch_stores)
        return self

    def __str__(self) -> str:
        only_fields, select_related, prefetch_related = self.compile()
        only = ",".join(only_fields)
        select = ",".join(select_related)
        prefetch = ",".join(item.prefetch_to for item in prefetch_related)
        return f"{only=}|{select=}|{prefetch=}"
