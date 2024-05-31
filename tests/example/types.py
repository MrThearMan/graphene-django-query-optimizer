# ruff: noqa: RUF012, I001
import graphene
from django.contrib.contenttypes.models import ContentType
from django.db.models import F, Model, QuerySet, Value
from django.db.models.functions import Concat, ExtractYear
from django_filters import CharFilter, OrderingFilter
from graphene import relay, Connection, ObjectType

from query_optimizer import DjangoObjectType
from query_optimizer.fields import (
    AnnotatedField,
    DjangoConnectionField,
    DjangoListField,
    MultiField,
    RelatedField,
    ManuallyOptimizedField,
)
from query_optimizer.filter import FilterSet
from query_optimizer.settings import optimizer_settings
from query_optimizer.typing import GQLInfo, Any, Union
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
    DeveloperProxy,
    Tag,
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


class PlainRelatedObjectType(ObjectType):
    x = graphene.Int()


class PlainObjectType(ObjectType):
    foo = graphene.String()
    bar = graphene.Field(PlainRelatedObjectType)


class PostalCodeType(DjangoObjectType):
    tags = DjangoListField(lambda: TagType)

    class Meta:
        model = PostalCode
        fields = [
            "pk",
            "code",
            "housing_companies",
            "tags",
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

    def resolve_name(root: HousingCompany, info: GQLInfo) -> str:
        return root.name

    def resolve_postal_code(root: HousingCompany, info: GQLInfo) -> PostalCode:
        return root.postal_code

    greeting = AnnotatedField(graphene.String, F("name"))

    def resolve_greeting(root: HousingCompany, info: GQLInfo) -> str:
        return f"Hello {root.name}!"

    alias_greeting = AnnotatedField(graphene.String, F("alias_greeting"), aliases={"alias_greeting": F("name")})

    def resolve_alias_greeting(root: HousingCompany, info: GQLInfo) -> str:
        return f"Hello {root.alias_greeting}!"


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
    real_estate_name = AnnotatedField(graphene.String, F("real_estate__name"))

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
        filter_fields = {
            "street_address": ["exact"],
            "building__name": ["exact"],
        }
        max_complexity = 10

    completion_year = AnnotatedField(graphene.Int, ExtractYear("completion_date"))

    share_range = MultiField(graphene.String, fields=["shares_start", "shares_end"])

    def resolve_share_range(root: Apartment, info: GQLInfo) -> str:
        return f"{root.shares_start} - {root.shares_end}"

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
    pre_field = ManuallyOptimizedField(
        graphene.String,
        args={
            "foo": graphene.Int(required=True),
            "bar": graphene.String(),
        },
    )

    class Meta:
        model = Owner
        fields = [
            "pk",
            "name",
            "email",
            "ownerships",
        ]

    @staticmethod
    def optimize_pre_field(queryset: QuerySet, info: GQLInfo, foo: int, bar: str = "") -> int:
        return queryset.annotate(pre_field=Concat("name", Value(f"-{foo}{bar}")))


class OwnershipType(DjangoObjectType):
    class Meta:
        model = Ownership
        fields = [
            "pk",
            "owner",
            "sale",
            "percentage",
        ]


# Generic Relations


class TaggedItemType(graphene.Union):
    class Meta:
        types = [
            PostalCodeType,
            DeveloperType,
        ]

    @classmethod
    def resolve_type(cls, instance: Model, info: GQLInfo) -> type[DjangoObjectType]:
        if isinstance(instance, PostalCode):
            return PostalCodeType
        if isinstance(instance, Developer):
            return DeveloperType
        msg = f"Unknown type: {instance}"
        raise TypeError(msg)


class ContentTypeType(DjangoObjectType):
    class Meta:
        model = ContentType
        fields = [
            "app_label",
            "model",
        ]


class TagType(DjangoObjectType):
    content_type = RelatedField(ContentTypeType)
    content_object = graphene.Field(TaggedItemType)

    def resolve_content_object(root: Tag, info: GQLInfo) -> Union[PostalCode, Developer]:
        return root.content_object

    class Meta:
        model = Tag
        fields = [
            "tag",
            "object_id",
            "content_type",
            "content_object",
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


class DeveloperNode(IsTypeOfProxyPatch, DjangoObjectType):
    housingcompany_set = DjangoConnectionField(lambda: HousingCompanyNode)
    housing_companies = DjangoListField("tests.example.types.HousingCompanyType", field_name="housingcompany_set")

    idx = graphene.Field(graphene.Int)

    def resolve_idx(root: DeveloperProxy, info: GQLInfo) -> int:
        return getattr(root, optimizer_settings.PREFETCH_PARTITION_INDEX, -1)

    housing_company_id = graphene.Field(graphene.Int)

    def resolve_housing_company_id(root: DeveloperProxy, info: GQLInfo) -> str:
        return getattr(root, "_prefetch_related_val_housingcompany_id", -1)

    class Meta:
        model = DeveloperProxy
        interfaces = (relay.Node,)
        connection_class = CustomConnection


class ApartmentNode(IsTypeOfProxyPatch, DjangoObjectType):
    sales = DjangoListField(SaleType)

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
        fields = ["id", "name", "street_address"]


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
        filter_fields = {
            "name": ["exact"],
        }
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
    developers = DjangoConnectionField(DeveloperNode)

    developers_alt = DjangoListField(DeveloperNode, field_name="developers")
    property_manager_alt = RelatedField(lambda: PropertyManagerNode, field_name="property_manager")
    real_estates_alt = DjangoListField(RealEstateNode, field_name="real_estates")

    idx = graphene.Field(graphene.Int)

    def resolve_idx(root: HousingCompanyProxy, info: GQLInfo) -> int:
        return getattr(root, optimizer_settings.PREFETCH_PARTITION_INDEX, -1)

    developer_id = graphene.Field(graphene.Int)

    def resolve_developer_id(root: HousingCompanyProxy, info: GQLInfo) -> list[int]:
        return getattr(root, "_prefetch_related_val_developer_id", -1)

    class Meta:
        model = HousingCompanyProxy
        interfaces = (relay.Node,)
        connection_class = CustomConnection
        filterset_class = HousingCompanyFilterSet


class PropertyManagerFilterSet(FilterSet):
    order_by = OrderingFilter(fields=["name"])

    class Meta:
        model = PropertyManager
        fields = ["name", "email"]


class PropertyManagerNode(IsTypeOfProxyPatch, DjangoObjectType):
    housing_companies = DjangoConnectionField(HousingCompanyNode)
    housing_companies_alt = DjangoConnectionField(HousingCompanyNode, field_name="housing_companies")

    class Meta:
        model = PropertyManagerProxy
        interfaces = (relay.Node,)
        connection_class = CustomConnection
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
    class Meta:
        model = Example
        fields = "__all__"


class ForwardOneToOneType(DjangoObjectType):
    class Meta:
        model = ForwardOneToOne
        fields = "__all__"


class ForwardManyToOneType(DjangoObjectType):
    class Meta:
        model = ForwardManyToOne
        fields = "__all__"


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
