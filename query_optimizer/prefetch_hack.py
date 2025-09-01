from __future__ import annotations

from collections import defaultdict
from typing import TYPE_CHECKING, TypeAlias
from unittest.mock import patch

from django.db.models import ManyToManyField
from django.db.models.fields.related_descriptors import _filter_prefetch_queryset

from .settings import optimizer_settings

if TYPE_CHECKING:
    from django.db.models import ManyToManyRel, Model, QuerySet

    from .typing import TModel

__all__ = [
    "evaluate_with_prefetch_hack",
    "register_for_prefetch_hack",
]


PrefetchHackCacheType: TypeAlias = defaultdict[str, defaultdict[str, set[str]]]
_PATH = f"{_filter_prefetch_queryset.__module__}.{_filter_prefetch_queryset.__name__}"


def evaluate_with_prefetch_hack(queryset: QuerySet[TModel]) -> list[TModel]:
    """Evaluates the given queryset with the prefetch hack applied."""
    with patch(_PATH, side_effect=_prefetch_hack):
        return list(queryset)  # If the optimizer did its job, the database query is executed here.


def register_for_prefetch_hack(queryset: QuerySet, field: ManyToManyField | ManyToManyRel) -> None:
    """
    Registers the through table of a many-to-many field for the prefetch hack.
    See `_prefetch_hack` for more information.
    """
    related_model: type[Model] = field.related_model  # type: ignore[assignment]
    db_table = related_model._meta.db_table
    field_name = field.remote_field.name

    forward_field: ManyToManyField
    forward_field = field if isinstance(field, ManyToManyField) else field.remote_field
    through = forward_field.m2m_db_table()

    cache: PrefetchHackCacheType = defaultdict(lambda: defaultdict(set))
    cache[db_table][field_name].add(through)

    key = optimizer_settings.PREFETCH_HACK_CACHE_KEY
    queryset._hints.setdefault(key, cache)


def _prefetch_hack(queryset: QuerySet, field_name: str, instances: list[Model]) -> QuerySet:
    """
    Patches the prefetch mechanism to not create duplicate joins in the SQL query.
    This is needed due to how filtering with many-to-many relations is implemented in Django,
    which creates new joins for consecutive filters for the same relation.
    See: https://docs.djangoproject.com/en/dev/topics/db/queries/#spanning-multi-valued-relationships

    For nested connection fields, a window function with a partition on the many-to-many field
    is used to limit the queryset. This adds an OUTER join for the through table of the many-to-many field.
    Then, when the prefetch queryset is filtered by `_filter_prefetch_queryset` to just the instances
    from the parent model, an INNER join is added to the through table. This creates unnecessary duplicates
    in the SQL query, which messes up the window function's partitioning. Therefore, this hack is needed
    to prevent the INNER join from being added.
    """
    key = optimizer_settings.PREFETCH_HACK_CACHE_KEY
    cache: PrefetchHackCacheType | None = queryset._hints.pop(key, None)
    if cache is not None:
        #
        # `filter_is_sticky` is set here just to prevent the `used_aliases` from being cleared
        # when the queryset is cloned for filtering in `_filter_prefetch_queryset`.
        # See: `django.db.models.sql.query.Query.chain`.
        queryset.query.filter_is_sticky = True
        #
        # Add the registered through tables for a given model and field to the Query's `used_aliases`.
        # This is passed along during the filtering that happens as a part of `_filter_prefetch_queryset`,
        # until `django.db.models.sql.query.Query.join`, which has access to it with its `reuse` argument.
        # There, this should prevent the method from adding a duplicate join.
        queryset.query.used_aliases = cache[queryset.model._meta.db_table][field_name]

    return _filter_prefetch_queryset(queryset, field_name, instances)
