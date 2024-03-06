# ruff: noqa: RUF012, I001
import graphene
from django.db.models import F, Model, QuerySet, Value
from django.db.models.functions import Concat
from django_filters import CharFilter, OrderingFilter
from graphene import relay, Connection

from query_optimizer import DjangoObjectType, required_annotations, required_fields
from query_optimizer.fields import DjangoConnectionField, DjangoListField
from query_optimizer.filter import FilterSet
from query_optimizer.typing import GQLInfo, Any
from tests.example.models import (
    Apartment,
    ApartmentProxy,
    Building,
    BuildingProxy,
    Developer,
    Example,
    ForwardManyToMany,
    ForwardManyToManyForRelated,
    ForwardManyToOne,
    ForwardManyToOneForRelated,
    ForwardOneToOne,
    ForwardOneToOneForRelated,
    HousingCompany,
    HousingCompanyProxy,
    Owner,
    Ownership,
    PostalCode,
    PropertyManager,
    PropertyManagerProxy,
    RealEstate,
    RealEstateProxy,
    ReverseManyToMany,
    ReverseManyToManyToForwardManyToMany,
    ReverseManyToManyToForwardManyToOne,
    ReverseManyToManyToForwardOneToOne,
    ReverseManyToManyToReverseManyToMany,
    ReverseManyToManyToReverseOneToMany,
    ReverseManyToManyToReverseOneToOne,
    ReverseOneToMany,
    ReverseOneToManyToForwardManyToMany,
    ReverseOneToManyToForwardManyToOne,
    ReverseOneToManyToForwardOneToOne,
    ReverseOneToManyToReverseManyToMany,
    ReverseOneToManyToReverseOneToMany,
    ReverseOneToManyToReverseOneToOne,
    ReverseOneToOne,
    ReverseOneToOneToForwardManyToMany,
    ReverseOneToOneToForwardManyToOne,
    ReverseOneToOneToForwardOneToOne,
    ReverseOneToOneToReverseManyToMany,
    ReverseOneToOneToReverseOneToMany,
    ReverseOneToOneToReverseOneToOne,
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
    housingcompany_set = DjangoListField("tests.example.types.HousingCompanyType")

    class Meta:
        model = Developer
        fields = [
            "pk",
            "name",
            "description",
            "housingcompany_set",
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


# Relay / Django-filters


class CustomConnection(Connection):
    class Meta:
        abstract = True

    total_count = graphene.Int()
    edge_count = graphene.Int()

    def resolve_total_count(root: Any, info: GQLInfo, **kwargs: Any) -> int:
        return root.length

    def resolve_edge_count(root: Any, info: GQLInfo, **kwargs: Any) -> int:
        return len(root.edges)


class IsTypeOfProxyPatch:
    @classmethod
    def is_type_of(cls, root: Any, info: GQLInfo) -> bool:
        if cls._meta.model._meta.proxy:
            return root._meta.model._meta.concrete_model == cls._meta.model._meta.concrete_model
        return super().is_type_of(root, info)


class ApartmentNode(IsTypeOfProxyPatch, DjangoObjectType):
    class Meta:
        model = ApartmentProxy
        max_complexity = 10
        connection_class = CustomConnection
        filter_fields = {
            "street_address": ["exact"],
            "building__name": ["exact"],
        }
        interfaces = (relay.Node,)


class BuildingFilterSet(FilterSet):
    order_by = OrderingFilter(fields=["name"])

    class Meta:
        model = Building
        fields = ["name", "street_address"]


class BuildingNode(IsTypeOfProxyPatch, DjangoObjectType):
    apartments = DjangoConnectionField(ApartmentNode)

    class Meta:
        model = BuildingProxy
        interfaces = (relay.Node,)
        filterset_class = BuildingFilterSet


class RealEstateNode(IsTypeOfProxyPatch, DjangoObjectType):
    building_set = DjangoConnectionField(BuildingNode)

    class Meta:
        model = RealEstateProxy
        interfaces = (relay.Node,)


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


class PropertyManagerFilterSet(FilterSet):
    order_by = OrderingFilter(fields=["name"])

    class Meta:
        model = PropertyManager
        fields = ["name", "email"]


class PropertyManagerNode(IsTypeOfProxyPatch, DjangoObjectType):
    housing_companies = DjangoConnectionField(HousingCompanyNode)

    class Meta:
        model = PropertyManagerProxy
        interfaces = (relay.Node,)
        filterset_class = PropertyManagerFilterSet


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
    foo = graphene.String()
    custom_relation = graphene.Int()

    class Meta:
        model = Example
        fields = "__all__"

    @required_annotations(foo=F("forward_one_to_one_field__name"))
    def resolve_foo(self: Example, info: GQLInfo) -> str:
        return self.foo

    @required_fields("named_relation__id")
    def resolve_custom_relation(parent: Example, info: GQLInfo) -> int:
        return parent.named_relation.id


class ForwardOneToOneType(DjangoObjectType):
    class Meta:
        model = ForwardOneToOne
        fields = "__all__"


class ForwardManyToOneType(DjangoObjectType):
    bar = graphene.String()

    class Meta:
        model = ForwardManyToOne
        fields = "__all__"

    @required_annotations(bar=F("name"))
    def resolve_bar(self: ForwardManyToOne, info: GQLInfo) -> str:
        return self.bar


class ForwardManyToManyType(DjangoObjectType):
    class Meta:
        model = ForwardManyToMany
        fields = "__all__"


class ReverseOneToOneType(DjangoObjectType):
    class Meta:
        model = ReverseOneToOne
        fields = "__all__"


class ReverseOneToManyType(DjangoObjectType):
    class Meta:
        model = ReverseOneToMany
        fields = "__all__"


class ReverseManyToManyType(DjangoObjectType):
    class Meta:
        model = ReverseManyToMany
        fields = "__all__"


class ForwardOneToOneForRelatedType(DjangoObjectType):
    class Meta:
        model = ForwardOneToOneForRelated
        fields = "__all__"


class ForwardManyToOneForRelatedType(DjangoObjectType):
    class Meta:
        model = ForwardManyToOneForRelated
        fields = "__all__"


class ForwardManyToManyForRelatedType(DjangoObjectType):
    class Meta:
        model = ForwardManyToManyForRelated
        fields = "__all__"


class ReverseOneToOneToForwardOneToOneType(DjangoObjectType):
    class Meta:
        model = ReverseOneToOneToForwardOneToOne
        fields = "__all__"


class ReverseOneToOneToForwardManyToOneType(DjangoObjectType):
    class Meta:
        model = ReverseOneToOneToForwardManyToOne
        fields = "__all__"


class ReverseOneToOneToForwardManyToManyType(DjangoObjectType):
    class Meta:
        model = ReverseOneToOneToForwardManyToMany
        fields = "__all__"


class ReverseOneToOneToReverseOneToOneType(DjangoObjectType):
    class Meta:
        model = ReverseOneToOneToReverseOneToOne
        fields = "__all__"


class ReverseOneToOneToReverseManyToOneType(DjangoObjectType):
    class Meta:
        model = ReverseOneToOneToReverseOneToMany
        fields = "__all__"


class ReverseOneToOneToReverseManyToManyType(DjangoObjectType):
    class Meta:
        model = ReverseOneToOneToReverseManyToMany
        fields = "__all__"


class ReverseOneToManyToForwardOneToOneType(DjangoObjectType):
    class Meta:
        model = ReverseOneToManyToForwardOneToOne
        fields = "__all__"


class ReverseOneToManyToForwardManyToOneType(DjangoObjectType):
    class Meta:
        model = ReverseOneToManyToForwardManyToOne
        fields = "__all__"


class ReverseOneToManyToForwardManyToManyType(DjangoObjectType):
    class Meta:
        model = ReverseOneToManyToForwardManyToMany
        fields = "__all__"


class ReverseOneToManyToReverseOneToOneType(DjangoObjectType):
    class Meta:
        model = ReverseOneToManyToReverseOneToOne
        fields = "__all__"


class ReverseOneToManyToReverseManyToOneType(DjangoObjectType):
    class Meta:
        model = ReverseOneToManyToReverseOneToMany
        fields = "__all__"


class ReverseOneToManyToReverseManyToManyType(DjangoObjectType):
    class Meta:
        model = ReverseOneToManyToReverseManyToMany
        fields = "__all__"


class ReverseManyToManyToForwardOneToOneType(DjangoObjectType):
    class Meta:
        model = ReverseManyToManyToForwardOneToOne
        fields = "__all__"


class ReverseManyToManyToForwardManyToOneType(DjangoObjectType):
    class Meta:
        model = ReverseManyToManyToForwardManyToOne
        fields = "__all__"


class ReverseManyToManyToForwardManyToManyType(DjangoObjectType):
    class Meta:
        model = ReverseManyToManyToForwardManyToMany
        fields = "__all__"


class ReverseManyToManyToReverseOneToOneType(DjangoObjectType):
    class Meta:
        model = ReverseManyToManyToReverseOneToOne
        fields = "__all__"


class ReverseManyToManyToReverseManyToOneType(DjangoObjectType):
    class Meta:
        model = ReverseManyToManyToReverseOneToMany
        fields = "__all__"


class ReverseManyToManyToReverseManyToManyType(DjangoObjectType):
    class Meta:
        model = ReverseManyToManyToReverseManyToMany
        fields = "__all__"
