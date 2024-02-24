from __future__ import annotations

from typing import TYPE_CHECKING

import django_filters
from graphene_django.utils import maybe_queryset

if TYPE_CHECKING:
    from django.db import models


__all__ = [
    "FilterSet",
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
