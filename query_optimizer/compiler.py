from __future__ import annotations

import contextlib
from typing import TYPE_CHECKING

from django.contrib.contenttypes.fields import GenericForeignKey, GenericRelation
from django.db.models import ForeignKey, Manager, ManyToOneRel, Model, QuerySet
from graphene.utils.str_converters import to_snake_case
from graphene_django.utils import maybe_queryset

from .ast import GraphQLASTWalker
from .errors import OptimizerError
from .optimizer import QueryOptimizer
from .prefetch_hack import fetch_in_context
from .settings import optimizer_settings
from .utils import is_optimized, optimizer_logger, swappable_by_subclassing

if TYPE_CHECKING:
    import graphene
    from django.db import models
    from graphene.types.definitions import GrapheneObjectType
    from graphql import FieldNode

    from .typing import PK, GQLInfo, Optional, TModel, ToManyField, ToOneField, Union


__all__ = [
    "OptimizationCompiler",
    "optimize",
    "optimize_single",
]


def optimize(
    queryset: QuerySet[TModel],
    info: GQLInfo,
    *,
    max_complexity: Optional[int] = None,
) -> QuerySet[TModel]:
    """Optimize the given queryset according to the field selections received in the GraphQLResolveInfo."""
    optimizer = OptimizationCompiler(info, max_complexity=max_complexity).compile(queryset)
    if optimizer is not None:
        queryset = optimizer.optimize_queryset(queryset)
        fetch_in_context(queryset)

    return queryset


def optimize_single(
    queryset: QuerySet[TModel],
    info: GQLInfo,
    *,
    pk: PK,
    max_complexity: Optional[int] = None,
) -> Optional[TModel]:
    """Optimize the given queryset for a single model instance by its primary key."""
    optimizer = OptimizationCompiler(info, max_complexity=max_complexity).compile(queryset)
    if optimizer is None:  # pragma: no cover
        return queryset.filter(pk=pk).first()

    queryset = optimizer.optimize_queryset(queryset.filter(pk=pk))
    fetch_in_context(queryset)

    # Shouldn't use .first(), as it can apply additional ordering, which would cancel the optimization.
    # The queryset should have the right model instance, since we started by filtering by its pk,
    # so we can just pick that out of the result cache (if it hasn't been filtered out).
    return next(iter(queryset), None)


@swappable_by_subclassing
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
        self.to_attr: Optional[str] = None
        super().__init__(info)

    def compile(self, queryset: Union[QuerySet, Manager, list[Model]]) -> Optional[QueryOptimizer]:
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
        try:
            self.run()

        # Allow known errors to be raised.
        except OptimizerError:  # pragma: no cover
            raise

        # Raise unknown errors if not allowed to skip optimization on error.
        except Exception as error:  # pragma: no cover
            optimizer_logger.warning("Something went wrong during the optimization process.", exc_info=error)
            if not optimizer_settings.SKIP_OPTIMIZATION_ON_ERROR:
                raise
            return None

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
        related_model: type[Model] | None,
    ) -> None:
        name = related_field.get_cache_name() or related_field.name
        optimizer = QueryOptimizer(model=related_model, info=self.info, name=name, parent=self.optimizer)

        if isinstance(related_field, GenericForeignKey):
            optimizer = self.optimizer.prefetch_related.setdefault(name, optimizer)
        else:
            optimizer = self.optimizer.select_related.setdefault(name, optimizer)

        if isinstance(related_field, ForeignKey):
            self.optimizer.related_fields.append(related_field.attname)

        if isinstance(related_field, GenericForeignKey):
            self.optimizer.related_fields.append(related_field.ct_field)
            self.optimizer.related_fields.append(related_field.fk_field)

        with self.use_optimizer(optimizer):
            super().handle_to_one_field(field_type, field_node, related_field, related_model)

    def handle_to_many_field(
        self,
        field_type: GrapheneObjectType,
        field_node: FieldNode,
        related_field: ToManyField,
        related_model: type[Model] | None,
    ) -> None:
        name = related_field.get_cache_name() or related_field.name
        alias = getattr(field_node.alias, "value", None)
        key = self.to_attr if self.to_attr is not None else alias if alias is not None else name
        self.to_attr = None

        optimizer = QueryOptimizer(model=related_model, info=self.info, name=name, parent=self.optimizer)
        optimizer = self.optimizer.prefetch_related.setdefault(key, optimizer)

        if isinstance(related_field, ManyToOneRel):
            optimizer.related_fields.append(related_field.field.attname)

        if isinstance(related_field, GenericRelation):
            optimizer.related_fields.append(related_field.object_id_field_name)
            optimizer.related_fields.append(related_field.content_type_field_name)

        with self.use_optimizer(optimizer):
            super().handle_to_many_field(field_type, field_node, related_field, related_model)

    def handle_total_count(self, field_type: GrapheneObjectType, field_node: FieldNode) -> None:
        self.optimizer.total_count = True

    def handle_custom_field(self, field_type: GrapheneObjectType, field_node: FieldNode) -> None:
        field_name = to_snake_case(field_node.name.value)
        field: Optional[graphene.Field] = field_type.graphene_type._meta.fields.get(field_name)
        if field is None:  # pragma: no cover
            msg = (
                f"Field '{field_node.name.value}' not found from object type '{field_type.graphene_type}'. "
                f"Cannot optimize custom field."
            )
            optimizer_logger.warning(msg)
            return None

        # `RelatedField`, `DjangoListField` and `DjangoConnectionField` can define a
        # 'field_name' attribute to specify the actual model field name.
        actual_field_name: Optional[str] = getattr(field, "field_name", None)
        if actual_field_name is not None:
            self.to_attr = field_name
            return self.handle_model_field(field_type, field_node, actual_field_name)

        if hasattr(field, "optimizer_hook") and callable(field.optimizer_hook):
            field.optimizer_hook(self)
            return None

        return None  # pragma: no cover

    @contextlib.contextmanager
    def use_optimizer(self, optimizer: QueryOptimizer) -> None:
        orig_optimizer = self.optimizer
        try:
            self.optimizer = optimizer
            yield
        finally:
            self.optimizer = orig_optimizer
