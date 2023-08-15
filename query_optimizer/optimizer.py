# ruff: noqa: SLF001

from django.db.models import Field, ManyToOneRel, Model, QuerySet
from graphene.types.definitions import GrapheneObjectType
from graphene.utils.str_converters import to_snake_case
from graphql import (
    FieldNode,
    FragmentSpreadNode,
    GraphQLField,
    InlineFragmentNode,
    SelectionNode,
)
from graphql.execution.execute import get_field_def

from .cache import get_from_query_cache, store_in_query_cache
from .store import QueryOptimizerStore
from .typing import PK, GQLInfo, TableName, TModel
from .utils import get_base_object_type, is_foreign_key_id

# TODO: relay edge and connection testing
# TODO: django-filters filtering testing


def optimize(queryset: QuerySet[TModel], info: GQLInfo) -> QuerySet[TModel]:
    field_type = get_field_type(info)
    selections = get_selections(info)
    if not selections:
        return queryset

    optimizer = QueryOptimizer(info)
    store = optimizer.optimize_selections(field_type, selections)

    # Pk stored in 'query_optimizer.types.DjangoObjectType.get_node'
    pk: PK = getattr(queryset, "_cached_model_pk", None)

    if pk is not None:
        table_name: TableName = queryset.model._meta.db_table
        cached_item = get_from_query_cache(info.operation, info.schema, table_name, pk, store)
        if cached_item is not None:
            queryset._result_cache = [cached_item]
    else:
        queryset = store.optimize_queryset(queryset)
        store_in_query_cache(info.operation, queryset, info.schema, store)

    return queryset


def get_field_type(info: GQLInfo) -> GrapheneObjectType:
    field_node = info.field_nodes[0]
    field_def = get_field_def(info.schema, info.parent_type, field_node)
    return get_base_object_type(field_def.type)


def get_selections(info: GQLInfo) -> tuple[SelectionNode, ...]:
    field_node = info.field_nodes[0]
    selection_set = field_node.selection_set
    return () if selection_set is None else selection_set.selections


class QueryOptimizer:
    def __init__(self, info: GQLInfo) -> None:
        self.info = info

    def optimize_selections(
        self,
        field_type: GrapheneObjectType,
        selections: tuple[SelectionNode, ...],
    ) -> QueryOptimizerStore:
        store = QueryOptimizerStore()

        for selection in selections:
            if isinstance(selection, FieldNode):
                self.optimize_field_node(field_type, selection, store)

            elif isinstance(selection, FragmentSpreadNode):
                self.optimize_fragment_spread(field_type, selection)

            elif isinstance(selection, InlineFragmentNode):
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
        selection_graphql_name = selection.name.value
        selection_graphql_field = field_type.fields.get(selection_graphql_name)
        if selection_graphql_field is None:
            return

        model: type[Model] = field_type.graphene_type._meta.model
        model_field_name = to_snake_case(selection_graphql_name)
        model_field: Field = model._meta.get_field(model_field_name)

        if not model_field.is_relation or is_foreign_key_id(model_field, model_field_name):
            store.only(model_field_name)

        elif model_field.many_to_one or model_field.one_to_one:
            self.handle_to_one(model_field_name, selection, selection_graphql_field, store)

        elif model_field.one_to_many or model_field.many_to_many:
            self.handle_to_many(model_field_name, selection, selection_graphql_field, model_field, store)

        else:
            msg = f">>> Unhandled selection: '{selection.name.value}'"
            raise ValueError(msg)

    def handle_to_one(
        self,
        model_field_name: str,
        selection: FieldNode,
        selection_graphql_field: GraphQLField,
        store: QueryOptimizerStore,
    ) -> None:
        if selection.selection_set is None:
            return

        selection_field_type = get_base_object_type(selection_graphql_field.type)
        nested_store = self.optimize_selections(
            selection_field_type,
            selection.selection_set.selections,
        )

        store.select_related(model_field_name, nested_store)

    def handle_to_many(  # noqa: PLR0913
        self,
        model_field_name: str,
        selection: FieldNode,
        selection_graphql_field: GraphQLField,
        model_field: Field,
        store: QueryOptimizerStore,
    ) -> None:
        if selection.selection_set is None:
            return

        selection_field_type = get_base_object_type(selection_graphql_field.type)
        nested_store = self.optimize_selections(
            selection_field_type,
            selection.selection_set.selections,
        )

        if isinstance(model_field, ManyToOneRel):  # Add connecting ID
            nested_store.only(model_field.field.name)

        related_queryset = model_field.related_model.objects.all()
        store.prefetch_related(model_field_name, nested_store, related_queryset)

    def optimize_fragment_spread(self, field_type: GrapheneObjectType, selection: FragmentSpreadNode) -> None:
        graphql_name = selection.name.value
        field_node = self.info.fragments[graphql_name]
        selections = field_node.selection_set.selections
        self.optimize_selections(field_type, selections)

    def optimize_inline_fragment(self, selection: InlineFragmentNode) -> None:
        fragment_type_name = selection.type_condition.name.value
        msg = f"TODO: {fragment_type_name}"
        raise NotImplementedError(msg)
