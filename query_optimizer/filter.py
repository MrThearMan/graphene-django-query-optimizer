from __future__ import annotations

from functools import cache
from typing import TYPE_CHECKING

from django.utils.module_loading import import_string
from django_filters import FilterSet

from .settings import optimizer_settings

if TYPE_CHECKING:
    from django.db import models


__all__ = [
    "FilterSet",
    "create_filterset",
    "default_filterset_class",
]


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
