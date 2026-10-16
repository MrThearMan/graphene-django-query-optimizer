from __future__ import annotations

import dataclasses
from typing import TYPE_CHECKING

from django.contrib.contenttypes.fields import GenericRelation
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import ManyToManyField, ManyToManyRel, Prefetch
from django.db.models.constants import LOOKUP_SEP
from django.db.models.functions import RowNumber
from graphene.utils.str_converters import to_snake_case
from graphene_django.registry import get_global_registry
from graphene_django.settings import graphene_settings

from .ast import get_model_field
from .filter_info import get_filter_info
from .prefetch_hack import register_for_prefetch_hack
from .settings import optimizer_settings
from .typing import cast
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
    from django.db.models import Model, QuerySet
    from django.db.models.expressions import Combinable

    from .types import DjangoObjectType
    from .typing import (
        Any,
        ExpressionKind,
        GQLInfo,
        GraphQLFilterInfo,
        Literal,
        ManualOptimizerMethod,
        TModel,
        ToManyField,
    )

__all__ = [
    "QueryOptimizer",
]


@dataclasses.dataclass
class OptimizationResults[TModel: models.Model]:
    queryset: QuerySet[TModel]
    name: str | None = None
    only_fields: list[str] = dataclasses.field(default_factory=list)
    related_fields: list[str] = dataclasses.field(default_factory=list)
    select_related: list[str] = dataclasses.field(default_factory=list)
    prefetch_related: list[Prefetch | str] = dataclasses.field(default_factory=list)

    def __add__(self, other: OptimizationResults) -> OptimizationResults:
        """Adding two compilation results together means extending the lookups to the other model."""
        # Nested results always have a name.
        other_name: str = other.name  # type: ignore[assignment]
        self.select_related.append(other_name)
        self.only_fields.extend(f"{other.name}{LOOKUP_SEP}{only}" for only in other.only_fields)
        self.related_fields.extend(f"{other.name}{LOOKUP_SEP}{only}" for only in other.related_fields)
        self.select_related.extend(f"{other.name}{LOOKUP_SEP}{select}" for select in other.select_related)

        for prefetch in other.prefetch_related:
            if isinstance(prefetch, str):
                self.prefetch_related.append(f"{other.name}{LOOKUP_SEP}{prefetch}")
            if isinstance(prefetch, Prefetch):
                prefetch.add_prefix(other_name)
                self.prefetch_related.append(prefetch)

        return self


@swappable_by_subclassing
class QueryOptimizer:
    """Creates optimized queryset based on the optimization data found by the OptimizationCompiler."""

    def __init__(
        self,
        model: type[Model] | None,
        info: GQLInfo,
        name: str | None = None,
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
        self.manual_optimizers: dict[str, ManualOptimizerMethod] = {}
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
        """Run all pre-optimization hooks on the object type matching the queryset's model."""
        object_type: DjangoObjectType | None = get_global_registry().get_type_for_model(queryset.model)
        pre_optimization_hook = getattr(object_type, "pre_optimization_hook", None)
        if callable(pre_optimization_hook):
            return pre_optimization_hook(queryset, self)

        return queryset

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
            # Only generic foreign keys have no model, and they are always prefetched.
            nested_queryset = optimizer.model._default_manager.all()  # type: ignore[union-attr]
            nested_filter_info = filter_info.get("children", {}).get(name, {})
            nested_results = optimizer.process(nested_queryset, nested_filter_info)

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
                results.prefetch_related.append(optimizer.name)  # type: ignore[arg-type]
                continue

            nested_queryset = optimizer.model._default_manager.all()
            nested_filter_info = filter_info.get("children", {}).get(name, {})
            nested_results = optimizer.process(nested_queryset, nested_filter_info)

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

        # Prefetch optimizers always have a parent with a model, and a name.
        parent_model: type[Model] = self.parent.model  # type: ignore[union-attr,assignment]
        field_name: str = self.name  # type: ignore[assignment]
        field = cast("ToManyField | None", get_model_field(parent_model, field_name))
        if field is None:
            msg = (
                f"Cannot find field {self.name!r} on model {parent_model.__name__!r}. "
                f"Cannot optimize nested pagination."
            )
            optimizer_logger.warning(msg)
            return queryset

        remote_field = field.remote_field
        remote_field_name: str = (
            remote_field.name  # .
            if isinstance(field, models.ManyToManyField | GenericRelation)
            else remote_field.attname  # type: ignore[union-attr]
        )

        order_by = self.get_prefetch_ordering(filter_info, model=queryset.model)

        pagination_args = validate_pagination_args(
            after=filter_info.get("filters", {}).get("after"),
            before=filter_info.get("filters", {}).get("before"),
            offset=filter_info.get("filters", {}).get("offset"),
            first=filter_info.get("filters", {}).get("first"),
            last=filter_info.get("filters", {}).get("last"),
            max_limit=filter_info.get("max_limit", graphene_settings.RELAY_CONNECTION_MAX_LIMIT),
        )

        if (
            self.total_count
            or pagination_args.get("last") is not None
            or pagination_args.get("after") is not None
            or pagination_args.get("size") is None
        ):
            # If the query asks for total count for a nested connection field,
            # or is trying to limit the number of items from the end of the list,
            # or the user has set the `max_size` for the field to None (=no limit),
            # annotate the models in the queryset with the total count for each partition.
            # This is optional, since there is a performance impact due to needing
            # to use a subquery for each partition.
            queryset = queryset.annotate(
                **{
                    optimizer_settings.PREFETCH_COUNT_KEY: SubqueryCount(
                        queryset.filter(**{remote_field_name: models.OuterRef(remote_field_name)}),
                    ),
                },
            )

        # Don't limit the queryset if no pagination arguments are given (and field `max_size=None`)
        if all(value is None for value in pagination_args.values()):
            return queryset

        size = pagination_args["size"]
        if pagination_args.get("last") is not None or pagination_args.get("after") is not None or size is None:
            queryset = calculate_slice_for_queryset(queryset, **pagination_args)
        else:
            cut = calculate_queryset_slice(
                after=pagination_args["after"],
                before=pagination_args["before"],
                first=pagination_args["first"],
                last=pagination_args["last"],
                size=size,
            )
            queryset = add_slice_to_queryset(queryset, start=models.Value(cut.start), stop=models.Value(cut.stop))

        if isinstance(field, ManyToManyField | ManyToManyRel):
            register_for_prefetch_hack(queryset, field)

        return (
            queryset
            # Add a row number to the queryset, and limit the rows for each
            # partition based on the given pagination arguments.
            .alias(
                **{
                    optimizer_settings.PREFETCH_PARTITION_INDEX: (
                        models.Window(
                            expression=RowNumber(),
                            partition_by=models.F(remote_field_name),
                            # "Meta.ordering" is typed with "Combinable", which "Window" does not accept.
                            order_by=order_by,  # type: ignore[arg-type]
                        )
                        - models.Value(1)  # Start from zero.
                    )
                },
            ).filter(**{
                f"{optimizer_settings.PREFETCH_PARTITION_INDEX}__gte": models.F(
                    optimizer_settings.PREFETCH_SLICE_START
                ),
                f"{optimizer_settings.PREFETCH_PARTITION_INDEX}__lt": models.F(optimizer_settings.PREFETCH_SLICE_STOP),
            })
        )

    def get_prefetch_ordering(self, filter_info: GraphQLFilterInfo, model: type[Model]) -> list[str | Combinable]:
        """Get the ordering for prefetch querysets."""
        order_by = filter_info.get("filters", {}).get("order_by", "")
        order_info: str | list[str] = self.process_order_by_filter(order_by) or ""

        # 'Graphene-django' uses a comma-separated string for ordering.
        # 'Graphene-django-extensions' uses a list of enums.
        order_info = order_info.split(",") if isinstance(order_info, str) else [str(x) for x in order_info]

        return (
            # Use the `order_by` from the filter info, if available
            [x for x in order_info if x]
            # Use the model's `Meta.ordering` if no `order_by` is given
            or list(model._meta.ordering or [])
            # No ordering if neither is available
            or []
        )

    def filter_queryset(self, queryset: QuerySet, filter_info: GraphQLFilterInfo) -> QuerySet:
        """Run all filtering based on the object type matching the queryset's model."""
        # Run filtering hooks on object types if they exist.
        object_type: DjangoObjectType | None = get_global_registry().get_type_for_model(queryset.model)
        filter_queryset = getattr(object_type, "filter_queryset", None)
        if callable(filter_queryset):
            queryset = filter_queryset(queryset, self.info)

        # Lastly, run filterset filtering, if any.
        filterset_class = filter_info.get("filterset_class")
        if filterset_class is None:
            return queryset

        filterset = filterset_class(
            data=self.process_filters(filter_info["filters"]),
            queryset=queryset,
            request=self.info.context,
        )
        if not filterset.is_valid():
            raise ValidationError(filterset.form.errors.as_json())

        return filterset.qs

    def process_order_by_filter(self, value: list[str] | str | None) -> list[str] | str | None:
        if not value:
            return value

        if isinstance(value, list):
            return [to_snake_case(item) for item in value if item]

        return to_snake_case(value)

    def process_filters(self, input_data: dict[str, Any]) -> dict[str, Any]:
        from graphene_django.filter.fields import convert_enum  # noqa: PLC0415

        kwargs = {}
        for key, value in input_data.items():
            v = convert_enum(value)

            if key == "order_by":
                v = self.process_order_by_filter(v)

            kwargs[key] = v

        return kwargs

    def run_manual_optimizers(self, queryset: QuerySet, filter_info: GraphQLFilterInfo) -> QuerySet:
        for name, func in self.manual_optimizers.items():
            filters: dict[str, Any] = filter_info.get("children", {}).get(name, {}).get("filters", {})
            queryset = func(queryset, self, **filters)
        return queryset

    def has_child_optimizer(self, name: str) -> bool:
        return name in self.select_related or name in self.prefetch_related

    def get_child_optimizer(self, name: str) -> QueryOptimizer | None:
        return self.select_related.get(name) or self.prefetch_related.get(name)

    def get_or_set_child_optimizer(
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
