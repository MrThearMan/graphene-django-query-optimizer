from django.db.models import ManyToOneRel, Model, QuerySet
from graphene.relay.connection import ConnectionOptions
from graphene.types.definitions import GrapheneObjectType
from graphene.utils.str_converters import to_snake_case
from graphene_django.types import DjangoObjectTypeOptions
from graphql import (
    FieldNode,
    FragmentSpreadNode,
    GraphQLField,
    InlineFragmentNode,
    SelectionNode,
)

from .cache import get_from_query_cache, store_in_query_cache
from .store import QueryOptimizerStore
from .typing import PK, PK_CACHE_KEY, GQLInfo, ModelField, ToManyField, TypeVar, Union
from .utils import get_field_type, get_selections, get_underlying_type, is_foreign_key_id, is_to_many, is_to_one

TModel = TypeVar("TModel", bound=Model)


__all__ = [
    "optimize",
    "QueryOptimizer",
]


def optimize(queryset: QuerySet[TModel], info: GQLInfo) -> QuerySet[TModel]:
    field_type = get_field_type(info)
    selections = get_selections(info)
    if not selections:  # pragma: no cover
        return queryset

    optimizer = QueryOptimizer(info)
    store = optimizer.optimize_selections(field_type, selections)

    # Pk stored in 'query_optimizer.types.DjangoObjectType.get_node'
    pk: PK = getattr(queryset, PK_CACHE_KEY, None)

    if pk is not None:
        cached_item = get_from_query_cache(info.operation, info.schema, queryset.model, pk, store)
        if cached_item is not None:
            queryset._result_cache = [cached_item]
            return queryset

    queryset = store.optimize_queryset(queryset, pk=pk)
    if optimizer.cache_results:
        store_in_query_cache(info.operation, queryset, info.schema, store)

    return queryset


class QueryOptimizer:
    def __init__(self, info: GQLInfo) -> None:
        self.info = info
        self.cache_results = True

    def optimize_selections(
        self,
        field_type: GrapheneObjectType,
        selections: tuple[SelectionNode, ...],
    ) -> QueryOptimizerStore:
        store = QueryOptimizerStore()

        for selection in selections:
            if isinstance(selection, FieldNode):
                self.optimize_field_node(field_type, selection, store)

            elif isinstance(selection, FragmentSpreadNode):  # pragma: no cover
                self.optimize_fragment_spread(field_type, selection, store)

            elif isinstance(selection, InlineFragmentNode):  # pragma: no cover
                self.optimize_inline_fragment(selection)

            else:  # pragma: no cover
                msg = f"Unhandled selection node: '{selection}'"
                raise TypeError(msg)

        return store

    def optimize_field_node(
        self,
        field_type: GrapheneObjectType,
        selection: FieldNode,
        store: QueryOptimizerStore,
    ) -> None:
        options: Union[DjangoObjectTypeOptions, ConnectionOptions] = field_type.graphene_type._meta

        if isinstance(options, ConnectionOptions):
            return self.handle_relay_node(field_type, selection, store)

        elif isinstance(options, DjangoObjectTypeOptions):
            return self.handle_regular_node(field_type, selection, store)

        else:  # pragma: no cover
            msg = f"Unhandled field options type: {options}"
            raise TypeError(msg)

    # noinspection PyTypeChecker
    def handle_regular_node(
        self,
        field_type: GrapheneObjectType,
        selection: FieldNode,
        store: QueryOptimizerStore,
    ) -> None:
        model: type[Model] = field_type.graphene_type._meta.model
        selection_graphql_name = selection.name.value
        selection_graphql_field = field_type.fields.get(selection_graphql_name)
        if selection_graphql_field is None:  # pragma: no cover
            return

        model_field_name = to_snake_case(selection_graphql_name)
        model_field: ModelField = model._meta.get_field(model_field_name)

        if not model_field.is_relation or is_foreign_key_id(model_field, model_field_name):
            store.only(model_field_name)

        elif is_to_one(model_field):
            self.handle_to_one(model_field_name, selection, selection_graphql_field, store)

        elif is_to_many(model_field):
            self.handle_to_many(model_field_name, selection, selection_graphql_field, model_field, store)

        else:  # pragma: no cover
            msg = f">>> Unhandled selection: '{selection.name.value}'"
            raise ValueError(msg)

    def handle_relay_node(
        self,
        field_type: GrapheneObjectType,
        selection: FieldNode,
        store: QueryOptimizerStore,
    ) -> None:
        if selection.selection_set is None:  # pragma: no cover
            return

        # Connection QuerySets are sliced, so the results
        # should be cached later in the connection field.
        self.cache_results = False

        node: FieldNode = selection.selection_set.selections[0]  # type: ignore[assignment]
        if node.selection_set is None:  # page info
            return

        edges_field = field_type.fields[selection.name.value]
        edge_type = get_underlying_type(edges_field.type)
        node_field = edge_type.fields[node.name.value]
        node_type = get_underlying_type(node_field.type)

        nested_store = self.optimize_selections(node_type, node.selection_set.selections)
        store += nested_store

    def handle_to_one(
        self,
        model_field_name: str,
        selection: FieldNode,
        selection_graphql_field: GraphQLField,
        store: QueryOptimizerStore,
    ) -> None:
        if selection.selection_set is None:  # pragma: no cover
            return

        selection_field_type = get_underlying_type(selection_graphql_field.type)
        nested_store = self.optimize_selections(
            selection_field_type,
            selection.selection_set.selections,
        )

        store.select_related(model_field_name, nested_store)

    def handle_to_many(
        self,
        model_field_name: str,
        selection: FieldNode,
        selection_graphql_field: GraphQLField,
        model_field: ToManyField,
        store: QueryOptimizerStore,
    ) -> None:
        if selection.selection_set is None:  # pragma: no cover
            return

        selection_field_type = get_underlying_type(selection_graphql_field.type)
        nested_store = self.optimize_selections(
            selection_field_type,
            selection.selection_set.selections,
        )

        if isinstance(model_field, ManyToOneRel):  # Add connecting ID
            nested_store.only(model_field.field.name)

        related_queryset: QuerySet[Model] = model_field.related_model.objects.all()
        store.prefetch_related(model_field_name, nested_store, related_queryset)

    def optimize_fragment_spread(
        self,
        field_type: GrapheneObjectType,
        selection: FragmentSpreadNode,
        store: QueryOptimizerStore,
    ) -> None:  # pragma: no cover
        graphql_name = selection.name.value
        field_node = self.info.fragments[graphql_name]
        selections = field_node.selection_set.selections
        fragment_store = self.optimize_selections(field_type, selections)
        store.only_fields += fragment_store.only_fields
        store.select_stores.update(fragment_store.select_stores)
        store.prefetch_stores.update(fragment_store.prefetch_stores)

    def optimize_inline_fragment(self, selection: InlineFragmentNode) -> None:  # pragma: no cover
        fragment_type_name = selection.type_condition.name.value
        msg = f"TODO: {fragment_type_name}"
        raise NotImplementedError(msg)
