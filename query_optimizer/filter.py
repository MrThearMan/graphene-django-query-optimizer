from __future__ import annotations

from functools import cache
from typing import TYPE_CHECKING

import django_filters
from django.utils.module_loading import import_string
from graphene_django.utils import maybe_queryset

from .settings import optimizer_settings

if TYPE_CHECKING:
    from django.db import models


__all__ = [
    "FilterSet",
    "create_filterset",
    "default_filterset_class",
]


class FilterSet(django_filters.FilterSet):
    @property
    def qs(self) -> models.QuerySet:
        if not hasattr(self, "_qs"):
            # Override the default `qs` property to include this.
            # It's needed to ensure that the `queryset._result_cache`
            # is not cleared when using `queryset.all()`
            qs = maybe_queryset(self.queryset)
            if self.is_bound:
                # ensure form validation before filtering
                # noinspection PyStatementEffect
                self.errors  # noqa: B018
                qs = self.filter_queryset(qs)
            # noinspection PyAttributeOutsideInit
            self._qs = qs
        return self._qs


@cache
def default_filterset_class() -> type[FilterSet]:
    if optimizer_settings.DEFAULT_FILTERSET_CLASS:  # pragma: no cover
        return import_string(optimizer_settings.DEFAULT_FILTERSET_CLASS)
    return FilterSet


def create_filterset(
    model: type[models.Model],
    fields: dict[str, list[str]],
) -> type[FilterSet]:
    name = f"{model._meta.object_name}FilterSet"
    meta = type("Meta", (), {"model": model, "fields": fields})
    filterset_class = default_filterset_class()
    return type(name, (filterset_class,), {"Meta": meta})  # type: ignore[return-type]
