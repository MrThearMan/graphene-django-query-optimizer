from __future__ import annotations

from typing import TYPE_CHECKING

import django_filters
from graphene_django.filter.utils import get_filterset_class
from graphene_django.utils import maybe_queryset

if TYPE_CHECKING:
    from django.db import models
    from graphene_django import DjangoObjectType

    from .typing import Any


__all__ = [
    "FilterSet",
    "get_filterset_for_object_type",
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


def get_filterset_for_object_type(object_type: type[DjangoObjectType]) -> type[FilterSet]:
    meta: dict[str, Any] = {
        "model": object_type._meta.model,
        "fields": object_type._meta.filter_fields,
        "filterset_base_class": FilterSet,
    }
    return get_filterset_class(object_type._meta.filterset_class, **meta)
