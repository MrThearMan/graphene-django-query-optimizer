from __future__ import annotations

from collections import defaultdict
from typing import TYPE_CHECKING
from weakref import WeakKeyDictionary

from .settings import optimizer_settings

if TYPE_CHECKING:
    from django.db.models import Model, QuerySet
    from graphql import GraphQLSchema

    from .store import QueryOptimizerStore
    from .typing import PK, Hashable, Iterable, Optional, QueryCache, TableName, TypeVar

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
    their selected fields (as determined by QueryOptimizerStore), and lastly
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
    store: QueryOptimizerStore,
) -> Optional[TModel]:
    """
    Get the given model instance from query cache.

    :param key: Any hashable value that is present only for the duration of
                a single request, e.g., 'info.operation'.
    :param schema: The GraphQLSchema object where the cache exists.
    :param model: The model type to look for.
    :param pk: The primary key of the model instance to look for.
    :param store: The QueryOptimizerStore describing the fields that
                  should have been fetched on the model instance.
    :return: The Model instance if it exists in the cache, None if not.
    """
    store_str = str(store)
    query_cache = get_query_cache(key, schema)
    return query_cache[model._meta.db_table][store_str].get(pk)


def store_in_query_cache(
    key: Hashable,
    items: Iterable[Model],
    schema: GraphQLSchema,
    store: QueryOptimizerStore,
) -> None:
    """
    Set all given models, as well as any related models joined to them
    as described by the given QueryOptimizerStore, to the query cache.

    :param key: Any hashable value that is present only for the duration of
                a single request, e.g., 'info.operation'.
    :param items: Model instances that should be stored in the query cache.
    :param schema: The GraphQLSchema object where the cache exists.
    :param store: The QueryOptimizerStore describing the fields that
                  are fetched on the model instances.
    """
    query_cache = get_query_cache(key, schema)
    items = list(items)  # For QuerySets, the database query will occur here
    annotations = _get_annotations(items[0])
    for item in items:
        _add_item(query_cache, item, annotations, store)


def _get_annotations(item: Model) -> list[str]:
    # Don't use 'queryset.query.annotations' since we cannot extract annotations
    # as cleanly from the model if some other iterable than a queryset is given.
    # (these results contain foreign key ids as well)
    model_builtins = {"_prefetched_objects_cache", "_state"}
    fields: set[str] = {field.name for field in item._meta.get_fields()}
    attributes: set[str] = set(item.__dict__)
    diff = attributes.difference(fields)
    return list(diff.difference(model_builtins))


def _add_item(query_cache: QueryCache, instance: Model, annotations: list[str], store: QueryOptimizerStore) -> None:
    store_str = str(store)
    if annotations:
        store_str += f"|{annotations=}"
    table_name: TableName = instance._meta.db_table
    query_cache[table_name][store_str][instance.pk] = instance
    _add_selected(query_cache, instance, store)
    _add_prefetched(query_cache, instance, store)


def _add_selected(query_cache: QueryCache, instance: Model, store: QueryOptimizerStore) -> None:
    for nested_name, nested_store in store.select_stores.items():
        nested_instance: Model = getattr(instance, nested_name)
        _add_item(query_cache, nested_instance, [], nested_store)


def _add_prefetched(query_cache: QueryCache, instance: Model, store: QueryOptimizerStore) -> None:
    for nested_name, (nested_store, _queryset) in store.prefetch_stores.items():
        selected: QuerySet[Model] = getattr(instance, nested_name).all()
        for select in selected:
            _add_item(query_cache, select, [], nested_store)
