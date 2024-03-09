from __future__ import annotations

from collections import defaultdict
from typing import TYPE_CHECKING
from weakref import WeakKeyDictionary

from .settings import optimizer_settings

if TYPE_CHECKING:
    from django.db.models import Model, QuerySet
    from graphql import GraphQLSchema

    from .optimizer import QueryOptimizer
    from .typing import PK, Hashable, Optional, QueryCache, TableName, TypeVar

    TModel = TypeVar("TModel", bound=Model)


__all__ = [
    "get_from_query_cache",
    "get_query_cache",
    "store_in_query_cache",
]


def get_query_cache(key: Hashable, schema: GraphQLSchema) -> QueryCache:
    """
    Get or create a cache for storing model instances.
    Cache is implemented as a WeakKeyDictionary on the given key,
    stored in the given schema object.

    Items in the cache are stored first by their database table, then by
    their selected fields (as determined by QueryOptimizer), and lastly
    by their primary key. The first two levels of the hierarchy are implemented
    as defaultdicts.

    :param key: Any hashable value that is present only for the duration of
                a single request, e.g., 'info.operation'.
    :param schema: The GraphQLSchema object where the cache will exist.
    :return: The cache.
    """
    cache = schema.extensions.setdefault(optimizer_settings.QUERY_CACHE_KEY, WeakKeyDictionary())
    return cache.setdefault(key, defaultdict(lambda: defaultdict(dict)))  # type: ignore[no-any-return]


def get_from_query_cache(
    key: Hashable,
    schema: GraphQLSchema,
    model: type[TModel],
    pk: PK,
    optimizer: QueryOptimizer,
) -> Optional[TModel]:
    """
    Get the given model instance from query cache.

    :param key: Any hashable value that is present only for the duration of
                a single request, e.g., 'info.operation'.
    :param schema: The GraphQLSchema object where the cache exists.
    :param model: The model type to look for.
    :param pk: The primary key of the model instance to look for.
    :param optimizer: The QueryOptimizer describing the fields that
                  should have been fetched on the model instance.
    :return: The Model instance if it exists in the cache, None if not.
    """
    optimizer_key = optimizer.cache_key
    query_cache = get_query_cache(key, schema)
    return query_cache[model._meta.db_table][optimizer_key].get(pk)


def store_in_query_cache(
    *,
    key: Hashable,
    queryset: QuerySet,
    schema: GraphQLSchema,
    optimizer: QueryOptimizer,
) -> None:
    """
    Set all given models, as well as any related models joined to them
    as described by the given QueryOptimizer, to the query cache.

    :param key: Any hashable value that is present only for the duration of
                a single request, e.g., 'info.operation'.
    :param queryset: QuerySet that should be stored in the query cache.
    :param schema: The GraphQLSchema object where the cache exists.
    :param optimizer: The QueryOptimizer describing the fields that
                      are fetched on the model instances.
    """
    query_cache = get_query_cache(key, schema)
    items = list(queryset)  # the database query will occur here
    if not items:
        return

    for item in items:
        _add_item(query_cache, item, optimizer)


def _add_item(query_cache: QueryCache, instance: Model, optimizer: QueryOptimizer) -> None:
    optimizer_key = optimizer.cache_key
    table_name: TableName = instance._meta.db_table
    query_cache[table_name][optimizer_key][instance.pk] = instance
    _add_selected(query_cache, instance, optimizer)
    _add_prefetched(query_cache, instance, optimizer)


def _add_selected(query_cache: QueryCache, instance: Model, optimizer: QueryOptimizer) -> None:
    for nested_name, nested_optimizer in optimizer.select_related.items():
        # For forward one-to-one and many-to-one, the relation might be null.
        # For reverse one-to-one, the relation might not exist.
        nested_instance: Optional[Model] = getattr(instance, nested_name, None)
        if nested_instance is not None:
            _add_item(query_cache, nested_instance, nested_optimizer)


def _add_prefetched(query_cache: QueryCache, instance: Model, optimizer: QueryOptimizer) -> None:
    for nested_name, nested_optimizer in optimizer.prefetch_related.items():
        # Here we can fetch the many-related items from the instance with `.all()`
        # without hitting the database, because the items have already been prefetched.
        # See: `django.db.models.fields.related_descriptors.RelatedManager.get_queryset`
        # and `django.db.models.fields.related_descriptors.ManyRelatedManager.get_queryset`
        selected: QuerySet[Model] = getattr(instance, nested_name).all()
        for select in selected:
            _add_item(query_cache, select, nested_optimizer)
