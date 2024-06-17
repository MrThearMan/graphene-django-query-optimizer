from __future__ import annotations

import dataclasses
from copy import copy
from typing import TYPE_CHECKING

from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Model, Prefetch, QuerySet
from django.db.models.constants import LOOKUP_SEP
from django.db.models.functions import RowNumber
from graphene_django.registry import get_global_registry
from graphene_django.settings import graphene_settings

from .ast import get_model_field
from .filter_info import get_filter_info
from .prefetch_hack import _register_for_prefetch_hack
from .settings import optimizer_settings
from .typing import Generic, TModel
from .utils import (
    SubqueryCount,
    add_slice_to_queryset,
    calculate_queryset_slice,
    calculate_slice_for_queryset,
    mark_optimized,
    optimizer_logger,
    swappable_by_subclassing,
)
from .validators import validate_pagination_args

if TYPE_CHECKING:
    from .types import DjangoObjectType
    from .typing import (
        Any,
        ExpressionKind,
        GQLInfo,
        GraphQLFilterInfo,
        Literal,
        Optional,
        QuerySetResolver,
        ToManyField,
    )

__all__ = [
    "QueryOptimizer",
]


@dataclasses.dataclass
class OptimizationResults(Generic[TModel]):
    name: str | None = None
    queryset: QuerySet[TModel] | None = None
    only_fields: list[str] = dataclasses.field(default_factory=list)
    related_fields: list[str] = dataclasses.field(default_factory=list)
    select_related: list[str] = dataclasses.field(default_factory=list)
    prefetch_related: list[Prefetch | str] = dataclasses.field(default_factory=list)

    def __add__(self, other: OptimizationResults) -> OptimizationResults:
        """Adding two compilation results together means extending the lookups to the other model."""
        self.select_related.append(other.name)
        self.only_fields.extend(f"{other.name}{LOOKUP_SEP}{only}" for only in other.only_fields)
        self.related_fields.extend(f"{other.name}{LOOKUP_SEP}{only}" for only in other.related_fields)
        self.select_related.extend(f"{other.name}{LOOKUP_SEP}{select}" for select in other.select_related)

        for prefetch in other.prefetch_related:
            if isinstance(prefetch, str):
                self.prefetch_related.append(f"{other.name}{LOOKUP_SEP}{prefetch}")
            if isinstance(prefetch, Prefetch):
                prefetch.add_prefix(other.name)
                self.prefetch_related.append(prefetch)

        return self


@swappable_by_subclassing
class QueryOptimizer:
    """Creates optimized queryset based on the optimization data found by the OptimizationCompiler."""

    def __init__(
        self,
        model: type[Model] | None,
        info: GQLInfo,
        name: Optional[str] = None,
        parent: QueryOptimizer | None = None,
    ) -> None:
        self.model = model
        self.info = info
        self.only_fields: list[str] = []
        self.related_fields: list[str] = []
        self.aliases: dict[str, ExpressionKind] = {}
        self.annotations: dict[str, ExpressionKind] = {}
        self.select_related: dict[str, QueryOptimizer] = {}
        self.prefetch_related: dict[str, QueryOptimizer] = {}
        self.manual_optimizers: dict[str, QuerySetResolver] = {}
        self.total_count: bool = False
        self.name = name
        self.parent: QueryOptimizer | None = parent

    def optimize_queryset(self, queryset: QuerySet[TModel]) -> QuerySet[TModel]:
        """
        Add the optimizations in this optimizer to the given queryset.

        :param queryset: QuerySet to optimize.
        """
        filter_info = get_filter_info(self.info, queryset.model)
        results = self.process(queryset, filter_info)
        return self.optimize(results, filter_info)

    def pre_processing(self, queryset: QuerySet[TModel]) -> QuerySet[TModel]:
        """Run all pre-optimization hooks on the objct type mathcing the queryset's model."""
        object_type: Optional[DjangoObjectType] = get_global_registry().get_type_for_model(queryset.model)
        if callable(getattr(object_type, "pre_optimization_hook", None)):
            return object_type.pre_optimization_hook(queryset, self)

        return queryset  # pragma: no cover

    def process(self, queryset: QuerySet[TModel], filter_info: GraphQLFilterInfo) -> OptimizationResults[TModel]:
        """Process compiled optimizations to optimize the given queryset."""
        queryset = self.pre_processing(queryset)
        queryset = self.run_manual_optimizers(queryset, filter_info)

        results = OptimizationResults(
            name=self.name,
            queryset=queryset,
            only_fields=self.only_fields,
            related_fields=self.related_fields,
        )

        for name, optimizer in self.select_related.items():
            queryset = optimizer.model._default_manager.all()
            nested_filter_info = filter_info.get("children", {}).get(name, {})
            nested_results = optimizer.process(queryset, nested_filter_info)

            # Promote `select_related` to `prefetch_related` if any annotations are needed.
            if optimizer.annotations:
                prefetch = optimizer.process_prefetch(name, nested_results, nested_filter_info)
                results.prefetch_related.append(prefetch)
                continue

            # Otherwise extend lookups to this model.
            results += nested_results

        for name, optimizer in self.prefetch_related.items():
            # For generic foreign keys, we don't know the model, so we can't optimize the queryset.
            if optimizer.model is None:
                results.prefetch_related.append(optimizer.name)
                continue

            queryset = optimizer.model._default_manager.all()
            nested_filter_info = filter_info.get("children", {}).get(name, {})
            nested_results = optimizer.process(queryset, nested_filter_info)

            prefetch = optimizer.process_prefetch(name, nested_results, nested_filter_info)
            results.prefetch_related.append(prefetch)

        return results

    def optimize(self, results: OptimizationResults[TModel], filter_info: GraphQLFilterInfo) -> QuerySet[TModel]:
        """Optimize the given queryset based on the optimization results."""
        queryset = results.queryset

        if results.select_related:
            queryset = queryset.select_related(*results.select_related)
        if results.prefetch_related:
            queryset = queryset.prefetch_related(*results.prefetch_related)
        if not optimizer_settings.DISABLE_ONLY_FIELDS_OPTIMIZATION and (results.only_fields or results.related_fields):
            queryset = queryset.only(*results.only_fields, *results.related_fields)
        if self.aliases:
            queryset = queryset.alias(**self.aliases)
        if self.annotations:
            queryset = queryset.annotate(**self.annotations)

        queryset = self.filter_queryset(queryset, filter_info)

        mark_optimized(queryset)
        return queryset

    def process_prefetch(self, to_attr: str, results: OptimizationResults, filter_info: GraphQLFilterInfo) -> Prefetch:
        """Process a prefetch, optimizing its queryset based on the given filter info."""
        queryset = self.optimize(results, filter_info)
        queryset = self.paginate_prefetch_queryset(queryset, filter_info)
        return Prefetch(self.name, queryset, to_attr=to_attr if to_attr != self.name else None)

    def paginate_prefetch_queryset(self, queryset: QuerySet, filter_info: GraphQLFilterInfo) -> QuerySet:
        """Paginate prefetch queryset based on the given filter info after it has been filtered."""
        # Only paginate nested connection fields.
        if not filter_info.get("is_connection", False):
            return queryset

        field: Optional[ToManyField] = get_model_field(self.parent.model, self.name)
        if field is None:  # pragma: no cover
            msg = (
                f"Cannot find field {self.name!r} on model {self.parent.model.__name__!r}. "
                f"Cannot optimize nested pagination."
            )
            optimizer_logger.warning(msg)
            return queryset

        remote_field = field.remote_field
        field_name = remote_field.name if isinstance(field, models.ManyToManyField) else remote_field.attname

        order_by: list[str] = (
            # Use the `order_by` from the filter info, if available
            [x for x in filter_info.get("filters", {}).get("order_by", "").split(",") if x]
            # Use the model's `Meta.ordering` if no `order_by` is given
            or copy(queryset.model._meta.ordering)
            # No ordering if neither is available
            or []
        )

        pagination_args = validate_pagination_args(
            after=filter_info.get("filters", {}).get("after"),
            before=filter_info.get("filters", {}).get("before"),
            offset=filter_info.get("filters", {}).get("offset"),
            first=filter_info.get("filters", {}).get("first"),
            last=filter_info.get("filters", {}).get("last"),
            max_limit=filter_info.get("max_limit", graphene_settings.RELAY_CONNECTION_MAX_LIMIT),
        )

        if self.total_count or pagination_args.get("last") is not None or pagination_args.get("size") is None:
            # If the query asks for total count for a nested connection field,
            # or is trying to limit the number of items from the end of the list,
            # or the user has set the `max_size` for the field to None (=no limit),
            # annotate the models in the queryset with the total count for each partition.
            # This is optional, since there is a performance impact due to needing
            # to use a subquery for each partition.
            queryset = queryset.annotate(
                **{
                    optimizer_settings.PREFETCH_COUNT_KEY: SubqueryCount(
                        queryset.filter(**{field_name: models.OuterRef(field_name)}),
                    ),
                },
            )

        # Don't limit the queryset if no pagination arguments are given (and field `max_size=None`)
        if all(value is None for value in pagination_args.values()):  # pragma: no cover
            return queryset

        if pagination_args.get("last") is not None or pagination_args.get("size") is None:
            queryset = calculate_slice_for_queryset(queryset, **pagination_args)
        else:
            cut = calculate_queryset_slice(**pagination_args)
            queryset = add_slice_to_queryset(queryset, start=models.Value(cut.start), stop=models.Value(cut.stop))

        _register_for_prefetch_hack(self.info, field)

        return (
            queryset
            # Add a row number to the queryset, and limit the rows for each
            # partition based on the given pagination arguments.
            .alias(
                **{
                    optimizer_settings.PREFETCH_PARTITION_INDEX: (
                        models.Window(
                            expression=RowNumber(),
                            partition_by=models.F(field_name),
                            order_by=order_by,
                        )
                        - models.Value(1)  # Start from zero.
                    )
                },
            ).filter(
                **{
                    f"{optimizer_settings.PREFETCH_PARTITION_INDEX}__gte": models.F(
                        optimizer_settings.PREFETCH_SLICE_START
                    ),
                    f"{optimizer_settings.PREFETCH_PARTITION_INDEX}__lt": models.F(
                        optimizer_settings.PREFETCH_SLICE_STOP
                    ),
                }
            )
        )

    def filter_queryset(self, queryset: QuerySet, filter_info: GraphQLFilterInfo) -> QuerySet:
        """Run all filtering based on the object type matching the queryset's model."""
        # Run filtering hooks on object types if they exist.
        object_type: Optional[DjangoObjectType] = get_global_registry().get_type_for_model(queryset.model)
        if callable(getattr(object_type, "filter_queryset", None)):
            queryset = object_type.filter_queryset(queryset, self.info)

        # Lastly, run filterset filtering, if any.
        if filter_info.get("filterset_class") is None:
            return queryset

        filterset = filter_info["filterset_class"](
            data=self.process_filters(filter_info["filters"]),
            queryset=queryset,
            request=self.info.context,
        )
        if not filterset.is_valid():  # pragma: no cover
            raise ValidationError(filterset.form.errors.as_json())

        return filterset.qs

    def process_filters(self, input_data: dict[str, Any]) -> dict[str, Any]:
        from graphene_django.filter.fields import convert_enum

        return {key: convert_enum(value) for key, value in input_data.items()}

    def run_manual_optimizers(self, queryset: QuerySet, filter_info: GraphQLFilterInfo) -> QuerySet:
        for name, func in self.manual_optimizers.items():
            filters: dict[str, Any] = filter_info.get("children", {}).get(name, {}).get("filters", {})
            queryset = func(queryset, self, **filters)
        return queryset

    def has_child_optimizer(self, name: str) -> bool:  # pragma: no cover
        return name in self.select_related or name in self.prefetch_related

    def get_child_optimizer(self, name: str) -> QueryOptimizer | None:  # pragma: no cover
        return self.select_related.get(name) or self.prefetch_related.get(name)

    def get_or_set_child_optimizer(  # pragma: no cover
        self,
        name: str,
        optimizer: QueryOptimizer,
        *,
        set_as: Literal["select_related", "prefetch_related"] = "select_related",
    ) -> QueryOptimizer:
        maybe_optimizer = self.select_related.get(name)
        if maybe_optimizer is not None:
            return maybe_optimizer
        maybe_optimizer = self.prefetch_related.get(name)
        if maybe_optimizer is not None:
            return maybe_optimizer
        getattr(self, set_as)[name] = optimizer
        return optimizer
