from __future__ import annotations

from contextlib import suppress
from typing import TYPE_CHECKING, Iterable, Optional, Union

import graphene
from django.core.exceptions import FieldDoesNotExist
from django.db.models import Expression, ForeignKey, Manager, ManyToOneRel, Model, QuerySet
from django.db.models.constants import LOOKUP_SEP
from graphene.relay.connection import ConnectionOptions
from graphene.utils.str_converters import to_snake_case
from graphene_django.types import DjangoObjectTypeOptions
from graphene_django.utils import maybe_queryset
from graphql import FieldNode, FragmentSpreadNode, GraphQLField, GraphQLOutputType, InlineFragmentNode, SelectionNode

from .cache import get_from_query_cache, store_in_query_cache
from .errors import OptimizerError
from .optimizer import QueryOptimizer
from .settings import optimizer_settings
from .utils import (
    get_field_type,
    get_selections,
    get_underlying_type,
    is_foreign_key_id,
    is_optimized,
    is_to_many,
    is_to_one,
    optimizer_logger,
)

if TYPE_CHECKING:
    from graphene.types.definitions import GrapheneObjectType, GrapheneUnionType

    from .typing import PK, GQLInfo, ModelField, ToManyField, ToOneField, TypeOptions, TypeVar

    TModel = TypeVar("TModel", bound=Model)


__all__ = [
    "optimize",
    "optimize_single",
    "OptimizationCompiler",
]


def optimize(
    queryset: QuerySet[TModel],
    info: GQLInfo,
    *,
    max_complexity: Optional[int] = None,
) -> QuerySet[TModel]:
    """Optimize the given queryset according to the field selections received in the GraphQLResolveInfo."""
    try:
        optimizer = OptimizationCompiler(info, max_complexity=max_complexity).compile(queryset)
        if optimizer is None:
            return queryset

        optimized_queryset = optimizer.optimize_queryset(queryset)
        store_in_query_cache(key=info.operation, queryset=optimized_queryset, schema=info.schema, optimizer=optimizer)
        return optimized_queryset  # noqa: TRY300

    except OptimizerError:  # pragma: no cover
        raise

    except Exception as error:  # noqa: BLE001  # pragma: no cover
        if not optimizer_settings.SKIP_OPTIMIZATION_ON_ERROR:
            raise

        optimizer_logger.warning("Something went wrong during the optimization process.", exc_info=error)
        return queryset


def optimize_single(
    queryset: QuerySet[TModel],
    info: GQLInfo,
    *,
    pk: PK,
    max_complexity: Optional[int] = None,
) -> Optional[TModel]:
    """Optimize the given queryset for a single model instance by its primary key."""
    queryset = queryset.filter(pk=pk)

    try:
        optimizer = OptimizationCompiler(info, max_complexity=max_complexity).compile(queryset)
        if optimizer is None:  # pragma: no cover
            return queryset.first()

        cached_item = get_from_query_cache(info.operation, info.schema, queryset.model, pk, optimizer)
        if cached_item is not None:
            return cached_item

        optimized_queryset = optimizer.optimize_queryset(queryset)
        store_in_query_cache(key=info.operation, queryset=optimized_queryset, schema=info.schema, optimizer=optimizer)

        # Shouldn't use .first(), as it can apply additional ordering, which would cancel the optimization.
        # The queryset should have the right model instance, since we started by filtering by its pk,
        # so we can just pick that out of the result cache (if it hasn't been filtered out).
        return next(iter(optimized_queryset._result_cache or []), None)

    except OptimizerError:  # pragma: no cover
        raise

    except Exception as error:  # noqa: BLE001  # pragma: no cover
        if not optimizer_settings.SKIP_OPTIMIZATION_ON_ERROR:
            raise

        optimizer_logger.warning("Something went wrong during the optimization process.", exc_info=error)
        return queryset.first()


class OptimizationCompiler:
    """Class for walking the GraphQL AST and compiling SQL optimizations based on the given query."""

    def __init__(self, info: GQLInfo, max_complexity: Optional[int] = None) -> None:
        """
        Initialize the optimization compiler with the query info.

        :param info: The GraphQLResolveInfo containing the query AST.
        :param max_complexity: How many 'select_related' and 'prefetch_related' table joins are allowed.
                               Used to protect from malicious queries.
        """
        self.info = info
        self.max_complexity = max_complexity or optimizer_settings.MAX_COMPLEXITY
        self.current_complexity = 0

    def increase_complexity(self) -> None:
        """Increase the current complexity, and check if it exceeds the maximum allowed."""
        self.current_complexity += 1
        if self.current_complexity > self.max_complexity:
            msg = f"Query complexity exceeds the maximum allowed of {self.max_complexity}"
            raise OptimizerError(msg)

    def compile(self, queryset: Union[QuerySet, Manager]) -> Optional[QueryOptimizer]:
        """
        Compile optimizations for the given queryset.

        :return: QueryOptimizer instance that can perform any needed optimization,
                                or None if queryset is already optimized.
        :raises OptimizerError: Something went wrong during the optimization process.
        """
        queryset = maybe_queryset(queryset)

        # If prior optimization has been done already, return early.
        if is_optimized(queryset):
            return None

        field_type = get_field_type(self.info)
        selections = get_selections(self.info)
        if not selections:  # pragma: no cover
            return None

        # Run the optimization compilation.
        optimizer = self.handle_selections(field_type, selections, queryset.model)

        # When resolving reverse one-to-many relations (other model has foreign key to this model),
        # if `known_related_fields` exist, they should be added to the optimizer, since they are used to linked
        # to the original model based on that field.
        if queryset._known_related_objects:  # pragma: no cover
            optimizer.related_fields += [row.attname for row in queryset._known_related_objects]

        return optimizer

    def handle_selections(
        self,
        field_type: Union[GrapheneObjectType, GrapheneUnionType],
        selections: tuple[SelectionNode, ...],
        model: type[Model],
    ) -> QueryOptimizer:
        optimizer = QueryOptimizer(model=model, info=self.info)

        for selection in selections:
            if isinstance(selection, FieldNode):
                self.handle_field_node(field_type, selection, optimizer)

            elif isinstance(selection, FragmentSpreadNode):
                self.handle_fragment_spread(field_type, selection, model, optimizer)

            elif isinstance(selection, InlineFragmentNode):
                self.handle_inline_fragment(field_type, selection, model, optimizer)

            else:  # pragma: no cover
                msg = f"Unhandled selection node: '{selection}'"
                raise OptimizerError(msg)

        return optimizer

    def handle_field_node(
        self,
        field_type: GrapheneObjectType,
        selection: FieldNode,
        optimizer: QueryOptimizer,
    ) -> None:
        options: TypeOptions = field_type.graphene_type._meta

        if isinstance(options, ConnectionOptions):
            return self.handle_connection_node(field_type, selection, optimizer)

        if isinstance(options, DjangoObjectTypeOptions):
            return self.handle_regular_node(field_type, selection, optimizer)

        msg = f"Unhandled field options type: {options}"  # pragma: no cover
        raise OptimizerError(msg)  # pragma: no cover

    def handle_regular_node(
        self,
        field_type: GrapheneObjectType,
        selection: FieldNode,
        optimizer: QueryOptimizer,
    ) -> None:
        model: type[Model] = field_type.graphene_type._meta.model
        selection_graphql_name = selection.name.value
        selection_graphql_field = field_type.fields.get(selection_graphql_name)
        if selection_graphql_field is None:
            return

        model_field_name, model_field = self.extract_model_field(model, selection_graphql_name)
        if model_field is None:
            selection_field = getattr(field_type.graphene_type, to_snake_case(selection_graphql_name), None)
            self.check_resolver_hints(selection_graphql_field, selection_field, model, optimizer)
            return

        if not model_field.is_relation or is_foreign_key_id(model_field, model_field_name):
            optimizer.only_fields.append(model_field_name)

        elif is_to_one(model_field):  # noinspection PyTypeChecker
            self.handle_to_one(model_field_name, selection, selection_graphql_field.type, model_field, optimizer)

        elif is_to_many(model_field):  # noinspection PyTypeChecker
            self.handle_to_many(model_field_name, selection, selection_graphql_field.type, model_field, optimizer)

        else:  # pragma: no cover
            msg = f"Unhandled selection: '{selection.name.value}'"
            raise OptimizerError(msg)

    def handle_connection_node(
        self,
        field_type: GrapheneObjectType,
        selection: FieldNode,
        optimizer: QueryOptimizer,
    ) -> None:
        if selection.selection_set is None:
            if selection.name.value == optimizer_settings.TOTAL_COUNT_FIELD:
                optimizer.total_count = True
            return

        gen = (selection for selection in selection.selection_set.selections if selection.name.value == "node")
        node: Optional[FieldNode] = next(gen, None)
        # Node was not requested, or nothing was requested from it, so we can skip this field
        if node is None or node.selection_set is None:
            return

        edges_field = field_type.fields[selection.name.value]
        edge_type = get_underlying_type(edges_field.type)
        node_field = edge_type.fields[node.name.value]
        node_type = get_underlying_type(node_field.type)
        node_model: type[Model] = node_type.graphene_type._meta.model

        nested_optimizer = self.handle_selections(node_type, node.selection_set.selections, node_model)
        optimizer += nested_optimizer

    def handle_to_one(
        self,
        model_field_name: str,
        selection: FieldNode,
        selection_field_type: GraphQLOutputType,
        model_field: ToOneField,
        optimizer: QueryOptimizer,
    ) -> None:
        if selection.selection_set is None:  # pragma: no cover
            return

        related_model: type[Model] = model_field.related_model  # type: ignore[assignment]
        if related_model == "self":  # pragma: no cover
            related_model = model_field.model

        selection_field_type = get_underlying_type(selection_field_type)

        self.increase_complexity()
        nested_optimizer = self.handle_selections(
            selection_field_type,
            selection.selection_set.selections,
            related_model,
        )

        if isinstance(model_field, ForeignKey):
            optimizer.related_fields.append(model_field.attname)

        optimizer.select_related[model_field_name] = nested_optimizer

    def handle_to_many(
        self,
        model_field_name: str,
        selection: FieldNode,
        selection_field_type: GraphQLOutputType,
        model_field: ToManyField,
        optimizer: QueryOptimizer,
    ) -> None:
        if selection.selection_set is None:  # pragma: no cover
            return

        related_model: type[Model] = model_field.related_model  # type: ignore[assignment]
        if related_model == "self":  # pragma: no cover
            related_model = model_field.model

        selection_field_type = get_underlying_type(selection_field_type)

        self.increase_complexity()
        nested_optimizer = self.handle_selections(
            selection_field_type,
            selection.selection_set.selections,
            related_model,
        )

        if isinstance(model_field, ManyToOneRel):
            nested_optimizer.related_fields.append(model_field.field.attname)

        optimizer.prefetch_related[model_field_name] = nested_optimizer

    def handle_fragment_spread(
        self,
        field_type: GrapheneObjectType,
        selection: FragmentSpreadNode,
        model: type[Model],
        optimizer: QueryOptimizer,
    ) -> None:
        graphql_name = selection.name.value
        field_node = self.info.fragments[graphql_name]
        selections = field_node.selection_set.selections
        nested_optimizer = self.handle_selections(field_type, selections, model)
        optimizer += nested_optimizer

    def handle_inline_fragment(
        self,
        field_type: GrapheneUnionType,
        selection: InlineFragmentNode,
        model: type[Model],
        optimizer: QueryOptimizer,
    ) -> None:
        fragment_type_name = selection.type_condition.name.value
        selection_graphql_field: Optional[GrapheneObjectType]
        selection_graphql_field = next((t for t in field_type.types if t.name == fragment_type_name), None)
        if selection_graphql_field is None:  # pragma: no cover
            return

        fragment_model: type[Model] = selection_graphql_field.graphene_type._meta.model
        if fragment_model != model:
            return

        selections = selection.selection_set.selections
        nested_optimizer = self.handle_selections(selection_graphql_field, selections, fragment_model)
        optimizer += nested_optimizer

    @staticmethod
    def extract_model_field(model: type[Model], selection_graphql_name: str) -> tuple[str, Optional[ModelField]]:
        model_field_name = to_snake_case(selection_graphql_name)

        if model_field_name == "pk":
            model_field: ModelField = model._meta.pk
            model_field_name = model_field.name  # use actual model pk name, e.g. 'id'
            return model_field_name, model_field

        with suppress(FieldDoesNotExist):
            model_field: ModelField = model._meta.get_field(model_field_name)
            return model_field_name, model_field

        # Field might be a reverse many-related field without `related_name`, in which case
        # the `model._meta.fields_map` will store the relation without the "_set" suffix.
        if model_field_name.endswith("_set"):
            with suppress(FieldDoesNotExist):
                model_field: ModelField = model._meta.get_field(model_field_name.removesuffix("_set"))
                if is_to_many(model_field):
                    return model_field_name, model_field

        return model_field_name, None

    def check_resolver_hints(
        self,
        graphql_field: GraphQLField,
        graphene_field: Union[graphene.Field, graphene.Scalar, None],
        model: type[Model],
        optimizer: QueryOptimizer,
    ) -> None:
        if isinstance(graphene_field, graphene.Scalar):
            resolver = graphql_field.resolve
        elif isinstance(graphene_field, graphene.Field):
            resolver = graphene_field.resolver
        else:  # pragma: no cover
            msg = f"Unhandled graphene field type: {graphene_field}"
            raise OptimizerError(msg)

        anns: dict[str, Expression] = getattr(resolver, "annotations", ())
        if anns:
            optimizer.annotations.update(anns)

        model_fields: list[ModelField] = model._meta.get_fields()

        relations: tuple[str, ...] = getattr(resolver, "relations", ())
        if relations:
            for relation in relations:
                with suppress(FieldDoesNotExist):
                    related_field = model._meta.get_field(relation)
                    if is_to_one(related_field):
                        hint_optimizer = QueryOptimizer(model=related_field.related_model, info=self.info)
                        optimizer.select_related[relation] = hint_optimizer
                    elif is_to_many(related_field):
                        hint_optimizer = QueryOptimizer(model=related_field.related_model, info=self.info)
                        optimizer.prefetch_related[relation] = hint_optimizer
                    else:
                        msg = f"Hinted related field {relation} is not a related field."
                        raise OptimizerError(msg)

        fields: tuple[str, ...] = getattr(resolver, "fields", ())
        for field_name in fields:
            hint_optimizer = QueryOptimizer(model=model, info=self.info)
            self.find_field_from_model(field_name, model_fields, hint_optimizer)
            optimizer += hint_optimizer

    def find_field_from_model(
        self,
        field_name: str,
        model_fields: Iterable[ModelField],
        optimizer: QueryOptimizer,
        prefix: str = "",
    ) -> None:
        for model_field in model_fields:
            model_field_name = model_field.name
            if prefix:
                model_field_name = f"{prefix}{LOOKUP_SEP}{model_field_name}"

            if field_name == model_field_name:
                optimizer.only_fields.append(model_field.name)
                return None

            # Check if the hint is to a related field, and if so, recurse into the related model.
            if not f"{field_name}{LOOKUP_SEP}".startswith(f"{model_field_name}{LOOKUP_SEP}"):
                continue

            related_model: type[Model] = model_field.related_model  # type: ignore[assignment]
            if related_model is None:  # pragma: no cover
                msg = (
                    f"Hint {model_field_name!r} seems to be for a related model,"
                    f"but no related model was not found: {field_name!r}"
                )
                raise OptimizerError(msg)

            if related_model == "self":  # pragma: no cover
                related_model = model_field.model

            self.increase_complexity()
            nested_optimizer = QueryOptimizer(model=related_model, info=self.info)

            if is_to_many(model_field):
                optimizer.prefetch_related[model_field.name] = nested_optimizer

            elif is_to_one(model_field):
                optimizer.select_related[model_field.name] = nested_optimizer

            else:  # pragma: no cover
                msg = f"Field {model_field} is not a related field."
                raise OptimizerError(msg)

            if isinstance(model_field, ManyToOneRel):
                nested_optimizer.related_fields.append(model_field.field.attname)

            related_model_fields: list[ModelField] = related_model._meta.get_fields()

            return self.find_field_from_model(
                field_name=field_name,
                prefix=model_field_name,
                optimizer=nested_optimizer,
                model_fields=related_model_fields,
            )

        msg = f"Field {field_name!r} not found in fields: {model_fields}."  # pragma: no cover
        raise OptimizerError(msg)  # pragma: no cover
