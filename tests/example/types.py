import graphene
from django.db.models import F, Model, QuerySet, Value
from django.db.models.functions import Concat
from django_filters import CharFilter, FilterSet, OrderingFilter
from graphene import relay

from query_optimizer import DjangoObjectType, optimize, required_fields
from query_optimizer.typing import GQLInfo
from query_optimizer.utils import can_optimize
from tests.example.models import (
    Apartment,
    ApartmentProxy,
    Building,
    Developer,
    HousingCompany,
    HousingCompanyProxy,
    Owner,
    Ownership,
    PostalCode,
    PropertyManager,
    RealEstate,
    Sale,
)

__all__ = [
    "ApartmentNode",
    "ApartmentType",
    "BuildingType",
    "DeveloperType",
    "HousingCompanyNode",
    "HousingCompanyType",
    "OwnershipType",
    "OwnerType",
    "People",
    "PostalCodeType",
    "PropertyManagerType",
    "RealEstateType",
    "SaleType",
]


# Basic


class PostalCodeType(DjangoObjectType):
    class Meta:
        model = PostalCode


class DeveloperType(DjangoObjectType):
    class Meta:
        model = Developer


class PropertyManagerType(DjangoObjectType):
    class Meta:
        model = PropertyManager


class HousingCompanyType(DjangoObjectType):
    class Meta:
        model = HousingCompany

    def resolve_name(model: HousingCompany, info: GQLInfo) -> str:
        return model.name

    greeting = graphene.String()
    manager = graphene.String()
    primary = graphene.String()

    @required_fields("name")
    def resolve_greeting(model: HousingCompany, info: GQLInfo) -> str:
        return f"Hello {model.name}!"

    @required_fields("property_manager__name")
    def resolve_manager(model: HousingCompany, info: GQLInfo) -> str:
        return model.property_manager.name

    @required_fields("real_estates__name")
    def resolve_primary(model: HousingCompany, info: GQLInfo) -> str:
        return model.real_estates.first().name


class RealEstateType(DjangoObjectType):
    class Meta:
        model = RealEstate


class BuildingType(DjangoObjectType):
    class Meta:
        model = Building


class ApartmentType(DjangoObjectType):
    @classmethod
    def max_complexity(cls) -> int:
        return 10

    class Meta:
        model = Apartment


class SaleType(DjangoObjectType):
    class Meta:
        model = Sale

    @classmethod
    def filter_queryset(cls, queryset: QuerySet, info: GQLInfo) -> QuerySet:
        if can_optimize(info):
            queryset = optimize(
                queryset.filter(purchase_price__gte=1),
                info,
                max_complexity=cls.max_complexity(),
                repopulate=True,
            )
        return queryset


class OwnerType(DjangoObjectType):
    class Meta:
        model = Owner


class OwnershipType(DjangoObjectType):
    class Meta:
        model = Ownership


# Relay


class ApartmentNode(DjangoObjectType):
    @classmethod
    def max_complexity(cls) -> int:
        return 10

    class Meta:
        model = ApartmentProxy
        filter_fields = {
            "street_address": ["exact"],
            "building__name": ["exact"],
        }
        interfaces = (relay.Node,)


# Django-filters


class HousingCompanyFilterSet(FilterSet):
    order_by = OrderingFilter(
        fields=[
            "name",
            "street_address",
            "postal_code__code",
            "city",
            "developers__name",
        ],
    )

    address = CharFilter(method="")

    class Meta:
        model = HousingCompany
        fields = {
            "name": ["iexact", "icontains"],
            "street_address": ["iexact", "icontains"],
            "postal_code__code": ["iexact"],
            "city": ["iexact", "icontains"],
            "developers__name": ["iexact", "icontains"],
        }

    def filter_address(self, qs: QuerySet[HousingCompany], name: str, value: str) -> QuerySet[HousingCompany]:
        return qs.alias(
            _address=Concat(
                F("street_address"),
                Value(", "),
                F("postal_code__code"),
                Value(" "),
                F("city"),
            ),
        ).filter(_address__icontains=value)


class HousingCompanyNode(DjangoObjectType):
    class Meta:
        model = HousingCompanyProxy
        interfaces = (relay.Node,)
        filterset_class = HousingCompanyFilterSet


# Union


class People(graphene.Union):
    class Meta:
        types = (
            DeveloperType,
            PropertyManagerType,
            OwnerType,
        )

    @classmethod
    def resolve_type(cls, instance: Model, info: GQLInfo) -> type[DjangoObjectType]:
        if isinstance(instance, Developer):
            return DeveloperType
        if isinstance(instance, PropertyManager):
            return PropertyManagerType
        if isinstance(instance, Owner):
            return OwnerType
        msg = f"Unknown type: {instance}"
        raise TypeError(msg)
