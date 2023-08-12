from collections import defaultdict
from typing import TYPE_CHECKING, Union
from weakref import WeakKeyDictionary

from django.db.models import Model, QuerySet
from graphql import GraphQLSchema

from .typing import PK, Hashable, Iterable, QueryCache, TableName, TypeVar

if TYPE_CHECKING:
    from .store import QueryOptimizerStore


TModel = TypeVar("TModel", bound=Model)


__all__ = [
    "get_from_query_cache",
    "get_query_cache",
    "store_in_query_cache",
]


def get_query_cache(key: Hashable, schema: GraphQLSchema) -> QueryCache:
    cache = schema.extensions.setdefault("_query_cache", WeakKeyDictionary())
    return cache.setdefault(key, defaultdict(lambda: defaultdict(dict)))  # type: ignore[no-any-return]


def get_from_query_cache(
    key: Hashable,
    schema: GraphQLSchema,
    model: type[TModel],
    pk: PK,
    store: "QueryOptimizerStore",
) -> Union[TModel, None]:
    """
    Get model instance from query cache for the given 'field_type'.
    Key should be any hashable value that is present only for the duration of
    a single request, e.g., 'info.operation'.
    """
    store_str = str(store)
    query_cache = get_query_cache(key, schema)
    return query_cache[model._meta.db_table][store_str].get(pk)


def store_in_query_cache(
    key: Hashable,
    items: Iterable[Model],
    schema: GraphQLSchema,
    store: "QueryOptimizerStore",
) -> None:
    """
    Set all models in list (as well as any select related models)
    to the query cache for the given 'field_type'.
    Key should be any hashable value that is present only for the duration of
    a single request, e.g., 'info.operation'.
    """
    query_cache = get_query_cache(key, schema)
    items = list(items)
    annotations = _get_annotations(items[0])
    for item in items:
        _add_item(query_cache, item, annotations, store)


def _get_annotations(item: Model) -> list[str]:
    # Don't use 'queryset.query.annotations' since we cannot extract annotations
    # as cleanly from the model if some other iterable is given.
    # (these results contain foreign key ids as well)
    model_builtins = {"_prefetched_objects_cache", "_state"}
    fields: set[str] = {field.name for field in item._meta.get_fields() if field.name not in model_builtins}
    attributes: set[str] = set(item.__dict__)
    return list(attributes.difference(fields))


def _add_item(query_cache: QueryCache, instance: Model, annotations: list[str], store: "QueryOptimizerStore") -> None:
    store_str = str(store)
    if annotations:
        store_str += f"|{annotations=}"
    table_name: TableName = instance._meta.db_table
    query_cache[table_name][store_str][instance.pk] = instance
    _add_selected(query_cache, instance, store)
    _add_prefetched(query_cache, instance, store)


def _add_selected(query_cache: QueryCache, instance: Model, store: "QueryOptimizerStore") -> None:
    for nested_name, nested_store in store.select_stores.items():
        nested_instance: Model = getattr(instance, nested_name)
        _add_item(query_cache, nested_instance, [], nested_store)


def _add_prefetched(query_cache: QueryCache, instance: Model, store: "QueryOptimizerStore") -> None:
    for nested_name, (nested_store, _queryset) in store.prefetch_stores.items():
        selected: QuerySet[Model] = getattr(instance, nested_name).all()
        for select in selected:
            _add_item(query_cache, select, [], nested_store)
