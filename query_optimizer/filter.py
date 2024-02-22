from __future__ import annotations

from typing import TYPE_CHECKING

import django_filters
import graphene_django.filter
from graphene_django.utils import maybe_queryset

from .fields import ConnectionFieldCachingMixin

if TYPE_CHECKING:
    from django.db import models

    from .typing import Any


__all__ = [
    "DjangoFilterConnectionField",
    "FilterSet",
]


class DjangoFilterConnectionField(
    ConnectionFieldCachingMixin,
    graphene_django.filter.DjangoFilterConnectionField,
):
    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        # Ensure that when filterset is created based on `Meta.filter_fields`,
        # it uses the custom `FilterSet` class that optimizes filtering properly.
        if self._extra_filter_meta is None:
            self._extra_filter_meta = {}
        self._extra_filter_meta.setdefault("filterset_base_class", FilterSet)


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
