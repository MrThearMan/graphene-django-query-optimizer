from django.db import models
from django.db.models import Prefetch, QuerySet
from django.db.models.constants import LOOKUP_SEP

from .typing import TModel


class QueryOptimizerStore:
    def __init__(self) -> None:
        self.only_list: list[str] = []
        self.select_stores: dict[str, "QueryOptimizerStore"] = {}
        self.prefetch_stores: dict[str, tuple["QueryOptimizerStore", QuerySet[TModel]]] = {}

    def only(self, field: str) -> None:
        self.only_list.append(field)

    def select_related(self, name: str, store: "QueryOptimizerStore") -> None:
        self.select_stores[name] = store

    def prefetch_related(self, name: str, store: "QueryOptimizerStore", queryset: QuerySet[models.Model]) -> None:
        self.prefetch_stores[name] = (store, queryset)

    def compile(self, in_prefetch: bool = False) -> tuple[list[str], list[str], list[Prefetch]]:
        only_list: list[str] = self.only_list.copy()
        select_related: list[str] = []
        prefetch_related: list[Prefetch] = []

        for name, store in self.select_stores.items():
            if not in_prefetch:
                select_related.append(name)
            self._compile_nested(store, name, only_list, select_related, prefetch_related, in_prefetch)

        for name, (store, queryset) in self.prefetch_stores.items():
            queryset = store.optimize_queryset(queryset)
            prefetch_related.append(Prefetch(name, queryset))
            self._compile_nested(store, name, only_list, select_related, prefetch_related, True)

        return only_list, select_related, prefetch_related

    @staticmethod
    def _compile_nested(
        store: "QueryOptimizerStore",
        name: str,
        only_list: list[str],
        select_related: list[str],
        prefetch_related: list[Prefetch],
        in_prefetch: bool,
    ) -> None:
        store_only_list, store_select_related, store_prefetch_related = store.compile(in_prefetch)
        for only in store_only_list:
            only_list.append(name + LOOKUP_SEP + only)
        for select in store_select_related:
            select_related.append(name + LOOKUP_SEP + select)
        for prefetch in store_prefetch_related:
            prefetch.add_prefix(name)
            prefetch_related.append(prefetch)

    def optimize_queryset(self, queryset: QuerySet[TModel]) -> QuerySet[TModel]:
        only_list, select_related, prefetch_related = self.compile()

        if only_list:
            queryset = queryset.only(*only_list)
        if select_related:
            queryset = queryset.select_related(*select_related)
        if prefetch_related:
            queryset = queryset.prefetch_related(*prefetch_related)

        return queryset

    def __str__(self) -> str:
        only_list, select_list, prefetch_list = self.compile()
        only = ",".join(only_list)
        select = ",".join(select_list)
        prefetch = ",".join(item.prefetch_to for item in prefetch_list)
        return f"{only=}|{select=}|{prefetch=}"
