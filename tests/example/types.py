import graphene
from django.db.models import Model
from graphene import relay

from query_optimizer import DjangoObjectType, required_fields
from query_optimizer.typing import GQLInfo
from tests.example.models import (
    Apartment,
    Building,
    Developer,
    HousingCompany,
    Owner,
    Ownership,
    PostalCode,
    PropertyManager,
    RealEstate,
    Sale,
)

__all__ = [
    "People",
    "ApartmentNode",
    "ApartmentType",
    "BuildingType",
    "DeveloperType",
    "HousingCompanyType",
    "OwnershipType",
    "OwnerType",
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
    class Meta:
        model = Apartment


class SaleType(DjangoObjectType):
    class Meta:
        model = Sale


class OwnerType(DjangoObjectType):
    class Meta:
        model = Owner


class OwnershipType(DjangoObjectType):
    class Meta:
        model = Ownership


# Relay


class ApartmentNode(DjangoObjectType):
    class Meta:
        model = Apartment
        filter_fields = {
            "street_address": ["exact"],
            "building__name": ["exact"],
        }
        interfaces = (relay.Node,)


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
