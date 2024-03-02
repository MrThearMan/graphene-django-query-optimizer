from __future__ import annotations

from functools import cache
from typing import TYPE_CHECKING

import django_filters
from django.utils.module_loading import import_string
from graphene_django.filter.utils import get_filtering_args_from_filterset, get_filterset_class
from graphene_django.utils import maybe_queryset

from .settings import optimizer_settings

if TYPE_CHECKING:
    from django.db import models
    from graphene_django import DjangoObjectType

    from .typing import Optional

__all__ = [
    "FilterSet",
    "get_filtering_args_from_filterset",
    "get_filterset_class_for_object_type",
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


def get_filterset_class_for_object_type(object_type: type[DjangoObjectType]) -> Optional[type[FilterSet]]:
    model = getattr(object_type._meta, "model", None)
    filter_fields = getattr(object_type._meta, "filter_fields", None)
    filterset_class = getattr(object_type._meta, "filterset_class", None)

    if model is None or (filterset_class is None and filter_fields is None):
        return None

    meta = {"model": model, "fields": filter_fields, "filterset_base_class": default_filterset_class()}
    return get_filterset_class(filterset_class, **meta)
