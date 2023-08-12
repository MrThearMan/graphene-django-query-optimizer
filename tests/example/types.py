from graphene import relay

from query_optimizer import DjangoObjectType
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
