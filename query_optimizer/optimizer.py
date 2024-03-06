from __future__ import annotations

import dataclasses
from typing import TYPE_CHECKING

from django.core.exceptions import FieldDoesNotExist, ValidationError
from django.db import models
from django.db.models import Expression, Model, Prefetch, QuerySet
from django.db.models.constants import LOOKUP_SEP
from django.db.models.functions import RowNumber
from graphene_django.registry import get_global_registry
from graphene_django.settings import graphene_settings

from .settings import optimizer_settings
from .utils import SubqueryCount, calculate_queryset_slice, get_filter_info, mark_optimized, optimizer_logger
from .validators import validate_pagination_args

if TYPE_CHECKING:
    from .types import DjangoObjectType
    from .typing import Any, GQLInfo, GraphQLFilterInfo, Optional, TypeVar

    TModel = TypeVar("TModel", bound=Model)


__all__ = [
    "QueryOptimizer",
]


@dataclasses.dataclass
class CompilationResults:
    only_fields: list[str] = dataclasses.field(default_factory=list)
    select_related: list[str] = dataclasses.field(default_factory=list)
    prefetch_related: list[Prefetch] = dataclasses.field(default_factory=list)

    @property
    def cache_key(self) -> str:
        only = ",".join(self.only_fields)
        select = ",".join(self.select_related)
        prefetch = ",".join(item.prefetch_to for item in self.prefetch_related)
        return f"{only=}|{select=}|{prefetch=}"


class QueryOptimizer:
    """Creates optimized queryset based on the optimization data found by the OptimizationCompiler."""

    def __init__(self, model: type[Model], info: GQLInfo) -> None:
        self.model = model
        self.info = info
        self.only_fields: list[str] = []
        self.related_fields: list[str] = []
        self.annotations: dict[str, Expression] = {}
        self.select_related: dict[str, QueryOptimizer] = {}
        self.prefetch_related: dict[str, QueryOptimizer] = {}
        self._cache_key: Optional[str] = None  # generated during optimization process

    def optimize_queryset(
        self,
        queryset: QuerySet[TModel],
        *,
        filter_info: Optional[GraphQLFilterInfo] = None,
    ) -> QuerySet[TModel]:
        """
        Add the optimizations in this optimizer to the given queryset.

        :param queryset: QuerySet to optimize.
        :param filter_info: Additional filtering info to use for the optimization.
        """
        if filter_info is None:
            filter_info = get_filter_info(self.info)

        results = self.compile(filter_info=filter_info)

        queryset = self.get_filtered_queryset(queryset)

        if filter_info is not None and filter_info.get("filterset_class") is not None:
            filterset = filter_info["filterset_class"](
                data=self.process_filters(filter_info["filters"]),
                queryset=queryset,
                request=self.info.context,
            )
            if not filterset.is_valid():  # pragma: no cover
                raise ValidationError(filterset.form.errors.as_json())

            queryset = filterset.qs

        if results.prefetch_related:
            queryset = queryset.prefetch_related(*results.prefetch_related)
        if results.select_related:
            queryset = queryset.select_related(*results.select_related)
        if not optimizer_settings.DISABLE_ONLY_FIELDS_OPTIMIZATION and (results.only_fields or self.related_fields):
            queryset = queryset.only(*results.only_fields, *self.related_fields)
        if self.annotations:
            queryset = queryset.annotate(**self.annotations)

        mark_optimized(queryset)
        return queryset

    def compile(self, *, filter_info: GraphQLFilterInfo) -> CompilationResults:
        results = CompilationResults(only_fields=self.only_fields.copy())

        for name, optimizer in self.select_related.items():
            # Promote select related to prefetch related if any annotations are needed.
            if optimizer.annotations:
                self.compile_prefetch(name, optimizer, results, filter_info)
            else:
                self.compile_select(name, optimizer, results, filter_info)

        for name, optimizer in self.prefetch_related.items():
            self.compile_prefetch(name, optimizer, results, filter_info)

        self._cache_key = results.cache_key
        return results

    def compile_select(
        self,
        name: str,
        optimizer: QueryOptimizer,
        results: CompilationResults,
        filter_info: GraphQLFilterInfo,
    ) -> None:
        results.select_related.append(name)
        nested_results = optimizer.compile(filter_info=filter_info)
        results.only_fields.extend(f"{name}{LOOKUP_SEP}{only}" for only in nested_results.only_fields)
        results.select_related.extend(f"{name}{LOOKUP_SEP}{select}" for select in nested_results.select_related)
        for prefetch in nested_results.prefetch_related:
            prefetch.add_prefix(name)
            results.prefetch_related.append(prefetch)

    def compile_prefetch(
        self,
        name: str,
        optimizer: QueryOptimizer,
        results: CompilationResults,
        filter_info: GraphQLFilterInfo,
    ) -> None:
        filter_info = filter_info.get("children", {}).get(name, {})
        queryset = optimizer.model._default_manager.all()
        queryset = optimizer.optimize_queryset(queryset, filter_info=filter_info)
        queryset = self.paginate_prefetch_queryset(queryset, name, filter_info=filter_info)
        results.prefetch_related.append(Prefetch(name, queryset))

    def paginate_prefetch_queryset(self, queryset: QuerySet, name: str, filter_info: GraphQLFilterInfo) -> QuerySet:
        """Paginate prefetch queryset based on the given filter info after it has been filtered."""
        # Only paginate nested connection fields.
        if not filter_info.get("is_connection", False):
            return queryset

        pagination_args = validate_pagination_args(
            after=filter_info.get("filters", {}).get("after"),
            before=filter_info.get("filters", {}).get("before"),
            offset=filter_info.get("filters", {}).get("offset"),
            first=filter_info.get("filters", {}).get("first"),
            last=filter_info.get("filters", {}).get("last"),
            # Just use `RELAY_CONNECTION_MAX_LIMIT` (ignore DjangoConnectionField.max_limit).
            max_limit=graphene_settings.RELAY_CONNECTION_MAX_LIMIT,
        )

        # If no pagination arguments are given, and `RELAY_CONNECTION_MAX_LIMIT` is `None`,
        # then don't limit the queryset.
        if all(value is None for value in pagination_args.values()):  # pragma: no cover
            return queryset

        cut = calculate_queryset_slice(**pagination_args)

        try:
            # Try to find the prefetch join field from the model to use for partitioning.
            field = self.model._meta.get_field(name)
        except FieldDoesNotExist:  # pragma: no cover
            msg = f"Cannot find field {name!r} on model {self.model.__name__!r}. Cannot optimize nested pagination."
            optimizer_logger.warning(msg)
            return queryset

        field_name: str = field.remote_field.attname
        order_by: Optional[list[str]] = (
            # Use the `order_by` from the filter info, if available
            [x for x in filter_info.get("filters", {}).get("order_by", "").split(",") if x]
            # Use the model's `Meta.ordering` if no `order_by` is given
            or queryset.model._meta.ordering
            # No ordering if neither is available
            or None
        )

        return (
            # Annotate the models in the queryset with the total count for each partition.
            # This needs to happen after the queryset has been filtered, but before
            # it's paginated with the window function.
            queryset.annotate(
                **{
                    optimizer_settings.OPTIMIZER_PREFETCH_COUNT_KEY: SubqueryCount(
                        queryset.filter(**{field_name: models.OuterRef(field_name)}),
                    ),
                },
            )
            # Add a row number to the queryset, and limit the rows for each
            # partition based on the given pagination arguments.
            .alias(
                _row_number=models.Window(
                    expression=RowNumber(),
                    partition_by=models.F(field_name),
                    order_by=order_by,
                )
            )
            .filter(_row_number__gte=cut.start, _row_number__lte=cut.stop)
        )

    def get_filtered_queryset(self, queryset: QuerySet[TModel]) -> QuerySet[TModel]:
        object_type: Optional[DjangoObjectType] = get_global_registry().get_type_for_model(queryset.model)
        if callable(getattr(object_type, "filter_queryset", None)):
            return object_type.filter_queryset(queryset, self.info)  # type: ignore[union-attr]
        return queryset  # pragma: no cover

    def process_filters(self, input_data: dict[str, Any]) -> dict[str, Any]:
        from graphene_django.filter.fields import convert_enum

        return {key: convert_enum(value) for key, value in input_data.items()}

    @property
    def cache_key(self) -> str:
        if self._cache_key is None:
            self.compile(filter_info={})
        return self._cache_key

    def __add__(self, other: QueryOptimizer) -> QueryOptimizer:
        self.only_fields += other.only_fields
        self.related_fields += other.related_fields
        self.annotations.update(other.annotations)
        self.select_related.update(other.select_related)
        self.prefetch_related.update(other.prefetch_related)
        return self

    def __str__(self) -> str:  # pragma: no cover
        return self.cache_key
