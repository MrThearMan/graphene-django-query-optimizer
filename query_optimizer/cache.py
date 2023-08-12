from collections import defaultdict
from typing import TYPE_CHECKING, Hashable
from weakref import WeakKeyDictionary

from django.db.models import Model, QuerySet
from graphql import GraphQLSchema

from .typing import PK, QueryCache, TableName

if TYPE_CHECKING:
    from .store import QueryOptimizerStore


def get_from_query_cache(
    key: Hashable,
    schema: GraphQLSchema,
    table_name: TableName,
    pk: PK,
    store: "QueryOptimizerStore",
) -> Model | None:
    """
    Get model instance from query cache for the given 'field_type'.
    Key should be any hashable value that is present only for the duration of
    a single request, e.g., 'info.operation'.
    """
    store_str = str(store)
    query_cache = get_query_cache(key, schema)
    return query_cache[table_name][store_str].get(pk)


def store_in_query_cache(
    key: Hashable,
    queryset: QuerySet[Model],
    schema: GraphQLSchema,
    store: "QueryOptimizerStore",
) -> None:
    """
    Set all models in the queryset (as well as any select related models)
    to the query cache for the given 'field_type'.
    Key should be any hashable value that is present only for the duration of
    a single request, e.g., 'info.operation'.
    """
    query_cache = get_query_cache(key, schema)
    for item in list(queryset):
        _add_item(query_cache, item, store)


def _add_item(query_cache: QueryCache, instance: Model, store: "QueryOptimizerStore") -> None:
    store_str = str(store)
    table_name: TableName = instance._meta.db_table
    query_cache[table_name][store_str][instance.pk] = instance
    _add_selected(query_cache, instance, store)
    _add_prefetched(query_cache, instance, store)


def _add_selected(query_cache: QueryCache, instance: Model, store: "QueryOptimizerStore") -> None:
    for nested_name, nested_store in store.select_stores.items():
        instance: Model = getattr(instance, nested_name)
        _add_item(query_cache, instance, nested_store)


def _add_prefetched(query_cache: QueryCache, instance: Model, store: "QueryOptimizerStore") -> None:
    for nested_name, (nested_store, _queryset) in store.prefetch_stores.items():
        selected: QuerySet[Model] = getattr(instance, nested_name).all()
        for select in selected:
            _add_item(query_cache, select, nested_store)


def get_query_cache(key: Hashable, schema: GraphQLSchema) -> QueryCache:
    schema.extensions.setdefault("_query_cache", WeakKeyDictionary())
    return schema.extensions["_query_cache"].setdefault(key, defaultdict(lambda: defaultdict(dict)))
