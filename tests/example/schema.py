import graphene
from django.db.models import QuerySet
from graphene_django.debug import DjangoDebug

from query_optimizer import GQLInfo, optimize

from .models import Apartment, HousingCompany
from .types import (
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
from .utils import count_queries


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

    def resolve_all_housing_companies(parent: None, info: GQLInfo) -> QuerySet[HousingCompany]:
        return optimize(HousingCompany.objects.all(), info)

    def resolve_all_apartments(parent: None, info: GQLInfo) -> QuerySet[Apartment]:
        return optimize(Apartment.objects.all(), info)

    # Single
    housing_company_by_name = graphene.List(HousingCompanyType, name=graphene.String(required=True))

    def resolve_housing_company_by_name(parent: None, info: GQLInfo, name: str) -> QuerySet[HousingCompany]:
        return optimize(HousingCompany.objects.filter(name=name), info)

    debug = graphene.Field(DjangoDebug, name="_debug")


class Schema(graphene.Schema):
    def execute(self, *args, **kwargs):
        with count_queries():
            return super().execute(*args, **kwargs)


schema = Schema(query=Query)
