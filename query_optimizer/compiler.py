from __future__ import annotations

import contextlib
from contextlib import suppress
from typing import TYPE_CHECKING, Iterable, Optional, Union

from django.core.exceptions import FieldDoesNotExist
from django.db.models import Expression, ForeignKey, Manager, ManyToOneRel, Model, QuerySet
from django.db.models.constants import LOOKUP_SEP
from graphene.utils.str_converters import to_snake_case
from graphene_django.utils import maybe_queryset

from .ast import GraphQLASTWalker, get_related_model, is_to_many, is_to_one
from .cache import get_from_query_cache, store_in_query_cache
from .errors import OptimizerError
from .optimizer import QueryOptimizer
from .settings import optimizer_settings
from .utils import is_optimized, optimizer_logger

if TYPE_CHECKING:
    from django.db import models
    from graphene.types.definitions import GrapheneObjectType
    from graphql import FieldNode

    from .typing import PK, GQLInfo, ModelField, ToManyField, ToOneField, TypeVar

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


class OptimizationCompiler(GraphQLASTWalker):
    """Class for compiling SQL optimizations based on the given query."""

    def __init__(self, info: GQLInfo, max_complexity: Optional[int] = None) -> None:
        """
        Initialize the optimization compiler with the query info.

        :param info: The GraphQLResolveInfo containing the query AST.
        :param max_complexity: How many 'select_related' and 'prefetch_related' table joins are allowed.
                               Used to protect from malicious queries.
        """
        self.max_complexity = max_complexity or optimizer_settings.MAX_COMPLEXITY
        self.optimizer: QueryOptimizer = None  # type: ignore[assignment]
        super().__init__(info)

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

        # Setup initial state.
        self.model = queryset.model
        self.optimizer = QueryOptimizer(model=queryset.model, info=self.info)

        # Walk the query AST to compile the optimizations.
        self.run()
        return self.optimizer

    def increase_complexity(self) -> None:
        super().increase_complexity()
        if self.complexity > self.max_complexity:
            msg = f"Query complexity exceeds the maximum allowed of {self.max_complexity}"
            raise OptimizerError(msg)

    def handle_normal_field(self, field_type: GrapheneObjectType, field_node: FieldNode, field: models.Field) -> None:
        self.optimizer.only_fields.append(field.get_attname())

    def handle_to_one_field(
        self,
        field_type: GrapheneObjectType,
        field_node: FieldNode,
        related_field: ToOneField,
        related_model: type[Model],
    ) -> None:
        name = related_field.get_cache_name() or related_field.name
        self.optimizer.select_related[name] = optimizer = QueryOptimizer(model=related_model, info=self.info)
        if isinstance(related_field, ForeignKey):
            self.optimizer.related_fields.append(related_field.attname)

        with self.use_optimizer(optimizer):
            super().handle_to_many_field(field_type, field_node, related_field, related_model)

    def handle_to_many_field(
        self,
        field_type: GrapheneObjectType,
        field_node: FieldNode,
        related_field: ToManyField,
        related_model: type[Model],
    ) -> None:
        name = related_field.get_cache_name() or related_field.name
        self.optimizer.prefetch_related[name] = optimizer = QueryOptimizer(model=related_model, info=self.info)
        if isinstance(related_field, ManyToOneRel):
            optimizer.related_fields.append(related_field.field.attname)

        with self.use_optimizer(optimizer):
            super().handle_to_many_field(field_type, field_node, related_field, related_model)

    def handle_total_count(self, field_type: GrapheneObjectType, field_node: FieldNode) -> None:
        self.optimizer.total_count = True

    def handle_custom_field(self, field_type: GrapheneObjectType, field_node: FieldNode) -> None:
        self.check_resolver_hints(field_type, field_node)

    def check_resolver_hints(self, field_type: GrapheneObjectType, field_node: FieldNode) -> None:
        field_name = to_snake_case(field_node.name.value)
        maybe_resolver = getattr(getattr(field_type.graphene_type, field_name, None), "resolver", None)

        anns: dict[str, Expression] = getattr(maybe_resolver, "annotations", {})
        relations: tuple[str, ...] = getattr(maybe_resolver, "relations", ())
        fields: tuple[str, ...] = getattr(maybe_resolver, "fields", ())

        maybe_resolver = getattr(field_type.fields.get(field_node.name.value, None), "resolve", None)

        anns.update(getattr(maybe_resolver, "annotations", {}))
        relations = (*relations, *getattr(maybe_resolver, "relations", ()))
        fields = (*fields, *getattr(maybe_resolver, "fields", ()))

        if anns:
            self.optimizer.annotations.update(anns)

        model_fields: list[ModelField] = self.model._meta.get_fields()

        if relations:
            for relation in relations:
                with suppress(FieldDoesNotExist):
                    related_field = self.model._meta.get_field(relation)
                    related_model = get_related_model(related_field, self.model)
                    if is_to_one(related_field):
                        hint_optimizer = QueryOptimizer(model=related_model, info=self.info)
                        self.optimizer.select_related[relation] = hint_optimizer
                    elif is_to_many(related_field):
                        hint_optimizer = QueryOptimizer(model=related_model, info=self.info)
                        self.optimizer.prefetch_related[relation] = hint_optimizer
                    else:
                        msg = f"Hinted related field {relation} is not a related field."
                        raise OptimizerError(msg)

        for field_name in fields:
            hint_optimizer = QueryOptimizer(model=self.model, info=self.info)
            self.find_field_from_model(field_name, model_fields, hint_optimizer)
            self.optimizer += hint_optimizer

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

    @contextlib.contextmanager
    def use_optimizer(self, optimizer: QueryOptimizer) -> GraphQLASTWalker:
        orig_optimizer = self.optimizer
        try:
            self.optimizer = optimizer
            yield
        finally:
            self.optimizer = orig_optimizer
