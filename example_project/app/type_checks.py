# mypy: warn-unused-ignores
"""
Static type checks for the generic DjangoObjectType.

mypy checks this module. The classes are defined only for type checking,
so they are not registered to the graphene registry.

The '# type: ignore[...]' comments are negative checks.
If mypy stops reporting the error, it reports the comment as unused.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, assert_type

if TYPE_CHECKING:
    from django.contrib.auth.models import User
    from django.db.models import QuerySet

    from example_project.app.models import Apartment, ApartmentQuerySet
    from query_optimizer import DjangoObjectType
    from query_optimizer.optimizer import QueryOptimizer
    from query_optimizer.typing import AnyUser, GQLInfo

    class ApartmentTypeWithQuerySet(DjangoObjectType[Apartment, User, ApartmentQuerySet]):
        @classmethod
        def pre_optimization_hook(cls, queryset: ApartmentQuerySet, optimizer: QueryOptimizer) -> ApartmentQuerySet:
            return queryset.with_rooms()

        @classmethod
        def filter_queryset(cls, queryset: ApartmentQuerySet, info: GQLInfo[User]) -> ApartmentQuerySet:
            return queryset.with_rooms()

        @classmethod
        def get_queryset(cls, queryset: ApartmentQuerySet, info: GQLInfo[User]) -> ApartmentQuerySet:
            return queryset.with_rooms()

    class ApartmentTypeWithDefaultQuerySet(DjangoObjectType[Apartment]):
        @classmethod
        def filter_queryset(cls, queryset: QuerySet[Apartment], info: GQLInfo[AnyUser]) -> QuerySet[Apartment]:
            return queryset.filter(rooms__isnull=False)

    def check_default_queryset(
        queryset: QuerySet[Apartment],
        info: GQLInfo[AnyUser],
        optimizer: QueryOptimizer,
    ) -> None:
        object_type = DjangoObjectType[Apartment]
        assert_type(object_type.pre_optimization_hook(queryset, optimizer), QuerySet[Apartment])
        assert_type(object_type.filter_queryset(queryset, info), QuerySet[Apartment])
        assert_type(object_type.get_queryset(queryset, info), QuerySet[Apartment])

    def check_user_without_queryset(
        queryset: QuerySet[Apartment],
        info: GQLInfo[User],
        optimizer: QueryOptimizer,
    ) -> None:
        object_type = DjangoObjectType[Apartment, User]
        assert_type(object_type.pre_optimization_hook(queryset, optimizer), QuerySet[Apartment])
        assert_type(object_type.filter_queryset(queryset, info), QuerySet[Apartment])
        assert_type(object_type.get_queryset(queryset, info), QuerySet[Apartment])

    def check_custom_queryset(
        queryset: ApartmentQuerySet,
        info: GQLInfo[User],
        optimizer: QueryOptimizer,
    ) -> None:
        object_type = DjangoObjectType[Apartment, User, ApartmentQuerySet]
        assert_type(object_type.pre_optimization_hook(queryset, optimizer), ApartmentQuerySet)
        assert_type(object_type.filter_queryset(queryset, info), ApartmentQuerySet)
        assert_type(object_type.get_queryset(queryset, info), ApartmentQuerySet)

    # A custom queryset needs the queryset type parameter.
    class ApartmentTypeWithWrongOverride(DjangoObjectType[Apartment]):
        @classmethod
        def filter_queryset(  # type: ignore[override]
            cls,
            queryset: ApartmentQuerySet,
            info: GQLInfo[AnyUser],
        ) -> ApartmentQuerySet:
            return queryset

    # The third type parameter is the queryset class, not the user type.
    class ApartmentTypeWithUserAsQuerySet(DjangoObjectType[Apartment, AnyUser, User]):  # type: ignore[type-var]
        pass
