import graphene
from django.db.models import F, Model, QuerySet, Value
from django.db.models.functions import Concat
from django_filters import CharFilter, FilterSet, OrderingFilter
from graphene import relay

from query_optimizer import DjangoConnectionField, DjangoObjectType, required_fields
from query_optimizer.typing import GQLInfo
from tests.example.models import (
    Apartment,
    ApartmentProxy,
    Building,
    BuildingProxy,
    Developer,
    Example,
    ForwardManyToMany,
    ForwardManyToOne,
    ForwardOneToOne,
    HousingCompany,
    HousingCompanyProxy,
    Owner,
    Ownership,
    PostalCode,
    PropertyManager,
    RealEstate,
    RealEstateProxy,
    ReverseManyToMany,
    ReverseOneToMany,
    ReverseOneToOne,
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
        fields = [
            "pk",
            "code",
            "housing_companies",
        ]


class DeveloperType(DjangoObjectType):
    class Meta:
        model = Developer
        fields = [
            "pk",
            "name",
            "description",
            "housing_companies",
        ]


class PropertyManagerType(DjangoObjectType):
    class Meta:
        model = PropertyManager
        fields = [
            "pk",
            "name",
            "email",
            "housing_companies",
        ]


class HousingCompanyType(DjangoObjectType):
    class Meta:
        model = HousingCompany
        fields = [
            "pk",
            "name",
            "street_address",
            "postal_code",
            "city",
            "developers",
            "property_manager",
            "real_estates",
        ]

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
        field = [
            "pk",
            "name",
            "housing_company",
            "buildings",
        ]


class BuildingType(DjangoObjectType):
    class Meta:
        model = Building
        fields = [
            "pk",
            "name",
            "street_address",
            "real_estate",
            "apartments",
        ]


class ApartmentType(DjangoObjectType):
    class Meta:
        model = Apartment
        fields = [
            "pk",
            "completion_date",
            "street_address",
            "stair",
            "floor",
            "apartment_number",
            "shares_start",
            "shares_end",
            "surface_area",
            "rooms",
            "building",
            "sales",
        ]
        max_complexity = 10

    @classmethod
    def filter_queryset(cls, queryset: QuerySet, info: GQLInfo) -> QuerySet:
        return queryset.filter(rooms__isnull=False)


class SaleType(DjangoObjectType):
    class Meta:
        model = Sale
        fields = [
            "pk",
            "apartment",
            "purchase_price",
            "purchase_date",
            "ownerships",
        ]

    @classmethod
    def filter_queryset(cls, queryset: QuerySet, info: GQLInfo) -> QuerySet:
        return queryset.filter(purchase_price__gte=1)


class OwnerType(DjangoObjectType):
    class Meta:
        model = Owner
        fields = [
            "pk",
            "name",
            "email",
            "sales",
            "ownerships",
        ]


class OwnershipType(DjangoObjectType):
    class Meta:
        model = Ownership
        fields = [
            "pk",
            "owner",
            "sale",
            "percentage",
        ]


# Relay


class IsTypeOfProxyPatch:
    @classmethod
    def is_type_of(cls, root, info):
        if cls._meta.model._meta.proxy:
            return root._meta.model._meta.concrete_model == cls._meta.model._meta.concrete_model
        return super().is_type_of(root, info)


class ApartmentNode(IsTypeOfProxyPatch, DjangoObjectType):
    class Meta:
        model = ApartmentProxy
        max_complexity = 10
        filter_fields = {
            "street_address": ["exact"],
            "building__name": ["exact"],
        }
        interfaces = (relay.Node,)


class BuildingNode(IsTypeOfProxyPatch, DjangoObjectType):
    apartments = DjangoConnectionField(ApartmentNode)

    class Meta:
        model = BuildingProxy
        interfaces = (relay.Node,)


class RealEstateNode(IsTypeOfProxyPatch, DjangoObjectType):
    buildings = DjangoConnectionField(BuildingNode)

    class Meta:
        model = RealEstateProxy
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

    address = CharFilter(method="filter_address")

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


class HousingCompanyNode(IsTypeOfProxyPatch, DjangoObjectType):
    real_estates = DjangoConnectionField(RealEstateNode)

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


# --------------------------------------------------------------------


class ExampleType(DjangoObjectType):
    class Meta:
        model = Example
        fields = [
            "id",
            "name",
            "forward_one_to_one_field",
            "forward_many_to_one_field",
            "forward_many_to_many_fields",
            "reverse_one_to_one_rel",
            "reverse_one_to_many_rels",
            "reverse_many_to_many_rels",
        ]
        interfaces = (relay.Node,)


class ForwardOneToOneType(DjangoObjectType):
    class Meta:
        model = ForwardOneToOne
        fields = [
            "id",
            "name",
            "example_rel",
        ]
        interfaces = (relay.Node,)


class ForwardManyToOneType(DjangoObjectType):
    class Meta:
        model = ForwardManyToOne
        fields = [
            "id",
            "name",
            "example_rels",
        ]
        interfaces = (relay.Node,)


class ForwardManyToManyType(DjangoObjectType):
    class Meta:
        model = ForwardManyToMany
        fields = [
            "id",
            "name",
            "example_rels",
        ]
        interfaces = (relay.Node,)


class ReverseOneToOneType(DjangoObjectType):
    class Meta:
        model = ReverseOneToOne
        fields = [
            "id",
            "name",
            "example_field",
        ]
        interfaces = (relay.Node,)


class ReverseOneToManyType(DjangoObjectType):
    class Meta:
        model = ReverseOneToMany
        fields = [
            "id",
            "name",
            "example_field",
        ]
        interfaces = (relay.Node,)


class ReverseManyToManyType(DjangoObjectType):
    class Meta:
        model = ReverseManyToMany
        fields = [
            "pk",
            "name",
            "example_fields",
        ]
        interfaces = (relay.Node,)
