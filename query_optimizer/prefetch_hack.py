from contextlib import nullcontext
from unittest.mock import patch
from weakref import WeakKeyDictionary

from django.db import models
from django.db.models.fields.related_descriptors import _filter_prefetch_queryset
from graphql import OperationDefinitionNode

from .typing import ContextManager, GQLInfo, ToManyField

__all__ = [
    "_register_for_prefetch_hack",
    "fetch_context",
]


# Use a weak key dictionary to make sure the saved values are cleared after the request ends.
_REUSABLE_M2M: WeakKeyDictionary[OperationDefinitionNode, set[str]] = WeakKeyDictionary()


def _register_for_prefetch_hack(info: GQLInfo, field: ToManyField) -> None:
    # Registers the through table of a many-to-many field for the prefetch hack.
    # See `_prefetch_hack` for more information.
    if not isinstance(field, (models.ManyToManyField, models.ManyToManyRel)):
        return

    through = field.m2m_db_table() if isinstance(field, models.ManyToManyField) else field.remote_field.m2m_db_table()
    # Use the info.operation as the key to make sure the saved values are cleared after the request ends.
    _REUSABLE_M2M.setdefault(info.operation, set()).add(through)


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
    # Add the registered through tables to the Query's `used_aliases`.
    # This is passed along during the filtering that happens as a part of `_filter_prefetch_queryset`,
    # until `django.db.models.sql.query.Query.join`, which has access to it with its `reuse` argument.
    # There, this should prevent the method from adding a duplicate join.
    queryset.query.used_aliases = {table for tables in _REUSABLE_M2M.values() for table in tables}
    #
    # Clear the hack once the queryset knows about the through tables.
    _REUSABLE_M2M.clear()
    return _filter_prefetch_queryset(queryset, field_name, instances)


_HACK_CONTEXT = patch(
    f"{_filter_prefetch_queryset.__module__}.{_filter_prefetch_queryset.__name__}",
    side_effect=_prefetch_hack,
)


def fetch_context() -> ContextManager:
    """Patches the prefetch mechanism if required."""
    return _HACK_CONTEXT if _REUSABLE_M2M else nullcontext()
