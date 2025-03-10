from __future__ import annotations

from functools import cache
from typing import TYPE_CHECKING

from django.utils.module_loading import import_string
from django_filters import FilterSet
from graphene_django.filter.utils import replace_csv_filters

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
    base = default_filterset_class()
    filterset_class: type[FilterSet] = type(name, (base,), {"Meta": meta})  # type: ignore[attr-defined]
    replace_csv_filters(filterset_class)
    return filterset_class
