from query_optimizer import DjangoObjectType, GQLInfo
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
    "PostalCodeType",
    "DeveloperType",
    "PropertyManagerType",
    "HousingCompanyType",
    "RealEstateType",
    "BuildingType",
    "ApartmentType",
    "SaleType",
    "OwnerType",
    "OwnershipType",
]


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
