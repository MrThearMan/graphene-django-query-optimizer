import graphene
from django.db import models
from django.db.models import F, QuerySet
from django.db.models.functions import Concat
from graphene import relay
from graphene_django.debug import DjangoDebug

from query_optimizer import optimize
from query_optimizer.filters import DjangoFilterConnectionField
from query_optimizer.typing import GQLInfo

from .models import (
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
from .types import (
    ApartmentNode,
    ApartmentType,
    BuildingType,
    DeveloperType,
    HousingCompanyType,
    OwnershipType,
    OwnerType,
    PostalCodeType,
    PropertyManagerType,
    RealEstateType,
    SaleType,
)


class Query(graphene.ObjectType):
    # List
    all_postal_codes = graphene.List(PostalCodeType)
    all_developers = graphene.List(DeveloperType)
    all_property_managers = graphene.List(PropertyManagerType)
    all_housing_companies = graphene.List(HousingCompanyType)
    all_real_estates = graphene.List(RealEstateType)
    all_buildings = graphene.List(BuildingType)
    all_apartments = graphene.List(ApartmentType)
    all_sales = graphene.List(SaleType)
    all_owners = graphene.List(OwnerType)
    all_ownerships = graphene.List(OwnershipType)

    def resolve_all_postal_codes(parent: None, info: GQLInfo) -> QuerySet[PostalCode]:
        return optimize(PostalCode.objects.all(), info)

    def resolve_all_developers(parent: None, info: GQLInfo) -> QuerySet[Developer]:
        return optimize(Developer.objects.all(), info)

    def resolve_all_property_managers(parent: None, info: GQLInfo) -> QuerySet[PropertyManager]:
        return optimize(PropertyManager.objects.all(), info)

    def resolve_all_housing_companies(parent: None, info: GQLInfo) -> QuerySet[HousingCompany]:
        return optimize(HousingCompany.objects.all(), info)

    def resolve_all_real_estates(parent: None, info: GQLInfo) -> QuerySet[RealEstate]:
        return optimize(RealEstate.objects.all(), info)

    def resolve_all_buildings(parent: None, info: GQLInfo) -> QuerySet[Building]:
        return optimize(Building.objects.all(), info)

    def resolve_all_apartments(parent: None, info: GQLInfo) -> QuerySet[Apartment]:
        return optimize(
            Apartment.objects.all().annotate(
                full_address=Concat(
                    F("street_address"),
                    F("floor"),
                    F("apartment_number"),
                    output_field=models.CharField(),
                ),
            ),
            info,
        )

    def resolve_all_sales(parent: None, info: GQLInfo) -> QuerySet[Sale]:
        return optimize(Sale.objects.all(), info)

    def resolve_all_owners(parent: None, info: GQLInfo) -> QuerySet[Owner]:
        return optimize(Owner.objects.all(), info)

    def resolve_all_ownerships(parent: None, info: GQLInfo) -> QuerySet[Ownership]:
        return optimize(Ownership.objects.all(), info)

    # Single
    housing_company_by_name = graphene.List(HousingCompanyType, name=graphene.String(required=True))

    def resolve_housing_company_by_name(parent: None, info: GQLInfo, name: str) -> QuerySet[HousingCompany]:
        return optimize(HousingCompany.objects.filter(name=name), info)

    # Relay fields

    apartment = relay.Node.Field(ApartmentNode)
    paged_apartments = DjangoFilterConnectionField(ApartmentNode)

    debug = graphene.Field(DjangoDebug, name="_debug")


schema = graphene.Schema(query=Query)
