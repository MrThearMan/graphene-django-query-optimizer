from __future__ import annotations

import contextlib
from collections import defaultdict
from contextlib import nullcontext
from typing import TYPE_CHECKING
from unittest.mock import patch
from weakref import WeakKeyDictionary

from django.db import models
from django.db.models.fields.related_descriptors import _filter_prefetch_queryset

if TYPE_CHECKING:
    from graphql import OperationDefinitionNode

    from .typing import ContextManager, GQLInfo, TModel, ToManyField, TypeAlias

__all__ = [
    "_register_for_prefetch_hack",
    "fetch_context",
]


_PrefetchCacheType: TypeAlias = defaultdict[str, defaultdict[str, set[str]]]
_PREFETCH_HACK_CACHE: WeakKeyDictionary[OperationDefinitionNode, _PrefetchCacheType] = WeakKeyDictionary()


def _register_for_prefetch_hack(info: GQLInfo, field: ToManyField) -> None:
    # Registers the through table of a many-to-many field for the prefetch hack.
    # See `_prefetch_hack` for more information.
    if not isinstance(field, (models.ManyToManyField, models.ManyToManyRel)):
        return

    forward_field: models.ManyToManyField = field.remote_field if isinstance(field, models.ManyToManyRel) else field
    db_table = field.related_model._meta.db_table
    field_name = field.remote_field.name
    through = forward_field.m2m_db_table()

    # Use the `info.operation` as the key to make sure the saved values are cleared after the request ends.
    cache = _PREFETCH_HACK_CACHE.setdefault(info.operation, defaultdict(lambda: defaultdict(set)))
    cache[db_table][field_name].add(through)


def _prefetch_hack(queryset: models.QuerySet, field_name: str, instances: list[models.Model]) -> models.QuerySet:
    """
    Patches the prefetch mechanism to not create duplicate joins in the SQL query.
    This is needed due to how filtering with many-to-many relations is implemented in Django,
    which creates new joins con consecutive filters for the same relation.
    See: https://docs.djangoproject.com/en/dev/topics/db/queries/#spanning-multi-valued-relationships

    For nested connection fields, a window function with a partition on the many-to-many field
    is used to limit the queryset. This adds an OUTER join for the through table of the many-to-many field.
    Then, when the prefetch queryset is filtered by `_filter_prefetch_queryset` to just the instances
    from the parent model, an INNER join is added to the through table. This creates unnecessary duplicates
    in the SQL query, which messes up the window function's partitioning. Therefore, this hack is needed
    to prevent the INNER join from being added.
    """
    #
    # `filter_is_sticky` is set here just to prevent the `used_aliases` from being cleared
    # when the queryset is cloned for filtering in `_filter_prefetch_queryset`.
    # See: `django.db.models.sql.query.Query.chain`.
    queryset.query.filter_is_sticky = True
    #
    # Cache is stored per-operation, so there should only be one top-level value.
    cache: _PrefetchCacheType = next(iter(_PREFETCH_HACK_CACHE.values()))
    #
    # Add the registered through tables for a given model and field to the Query's `used_aliases`.
    # This is passed along during the filtering that happens as a part of `_filter_prefetch_queryset`,
    # until `django.db.models.sql.query.Query.join`, which has access to it with its `reuse` argument.
    # There, this should prevent the method from adding a duplicate join.
    queryset.query.used_aliases = cache[queryset.model._meta.db_table][field_name]

    return _filter_prefetch_queryset(queryset, field_name, instances)


_HACK_CONTEXT = patch(
    f"{_filter_prefetch_queryset.__module__}.{_filter_prefetch_queryset.__name__}",
    side_effect=_prefetch_hack,
)


@contextlib.contextmanager
def fetch_context() -> ContextManager:
    """Patches the prefetch mechanism if required."""
    try:
        with _HACK_CONTEXT if _PREFETCH_HACK_CACHE else nullcontext():
            yield
    finally:
        _PREFETCH_HACK_CACHE.clear()


def fetch_in_context(queryset: models.QuerySet[TModel]) -> list[TModel]:
    """Evaluates the queryset with the prefetch hack applied."""
    with fetch_context():
        return list(queryset)  # the database query is executed here
