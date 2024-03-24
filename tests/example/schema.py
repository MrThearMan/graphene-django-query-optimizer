import itertools

import graphene
from django.db import models
from django.db.models.functions import Concat
from graphene import relay
from graphene_django.debug import DjangoDebug

from query_optimizer import optimize
from query_optimizer.fields import DjangoConnectionField, DjangoListField
from query_optimizer.typing import GQLInfo, Iterable, Union

from .models import (
    Apartment,
    Developer,
    Example,
    HousingCompany,
    Owner,
    PropertyManager,
)
from .types import (
    ApartmentNode,
    ApartmentType,
    BuildingNode,
    BuildingType,
    DeveloperNode,
    DeveloperType,
    ExampleType,
    HousingCompanyNode,
    HousingCompanyType,
    OwnershipType,
    OwnerType,
    People,
    PostalCodeType,
    PropertyManagerNode,
    PropertyManagerType,
    RealEstateNode,
    RealEstateType,
    SaleType,
)


class Query(graphene.ObjectType):
    all_postal_codes = DjangoListField(PostalCodeType)
    all_developers = DjangoListField(DeveloperType)
    all_property_managers = DjangoListField(PropertyManagerType)
    all_housing_companies = DjangoListField(HousingCompanyType)
    all_real_estates = DjangoListField(RealEstateType)
    all_buildings = DjangoListField(BuildingType)
    all_apartments = DjangoListField(ApartmentType)
    all_sales = DjangoListField(SaleType)
    all_owners = DjangoListField(OwnerType)
    all_ownerships = DjangoListField(OwnershipType)

    def resolve_all_apartments(parent: None, info: GQLInfo, **kwargs) -> models.QuerySet[Apartment]:
        return optimize(
            Apartment.objects.all().annotate(
                full_address=Concat(
                    models.F("street_address"),
                    models.F("floor"),
                    models.F("apartment_number"),
                    output_field=models.CharField(),
                ),
            ),
            info,
        )

    housing_company_by_name = graphene.List(HousingCompanyType, name=graphene.String(required=True))

    def resolve_housing_company_by_name(parent: None, info: GQLInfo, name: str) -> models.QuerySet[HousingCompany]:
        return optimize(HousingCompany.objects.filter(name=name), info)

    developer = relay.Node.Field(DeveloperNode)
    paged_developers = DjangoConnectionField(DeveloperNode)
    apartment = relay.Node.Field(ApartmentNode)
    paged_apartments = DjangoConnectionField(ApartmentNode)
    building = relay.Node.Field(BuildingNode)
    paged_buildings = DjangoConnectionField(BuildingNode)
    real_estate = relay.Node.Field(RealEstateNode)
    paged_real_estates = DjangoConnectionField(RealEstateNode)
    housing_company = relay.Node.Field(HousingCompanyNode)
    paged_housing_companies = DjangoConnectionField(HousingCompanyNode)
    property_managers = relay.Node.Field(PropertyManagerNode)
    paged_property_managers = DjangoConnectionField(PropertyManagerNode)

    all_people = graphene.List(People)

    def resolve_all_people(parent: None, info: GQLInfo) -> Iterable[Union[Developer, PropertyManager, Owner]]:
        developers = optimize(Developer.objects.all(), info)
        property_managers = optimize(PropertyManager.objects.all(), info)
        owners = optimize(Owner.objects.all(), info)
        return itertools.chain(developers, property_managers, owners)

    # --------------------------------------------------------------------

    example = graphene.Field(ExampleType, pk=graphene.Int(required=True))
    examples = DjangoListField(ExampleType)

    def resolve_example(parent: None, info: GQLInfo, pk: int = None):
        return optimize(Example.objects.filter(pk=pk), info).first()

    # --------------------------------------------------------------------

    debug = graphene.Field(DjangoDebug, name="_debug")


schema = graphene.Schema(query=Query)
