from __future__ import annotations

import itertools
from typing import TYPE_CHECKING

import graphene
from django.db import models
from django.db.models.functions import Concat
from graphene import relay
from graphene_django.debug import DjangoDebug

from query_optimizer import optimize
from query_optimizer.fields import DjangoConnectionField, DjangoListField
from query_optimizer.selections import get_field_selections

from .models import Apartment, Developer, Example, HousingCompany, Owner, PropertyManager
from .types import (
    ApartmentNode,
    ApartmentType,
    BuildingNode,
    BuildingType,
    ContentTypeType,
    DeveloperNode,
    DeveloperType,
    ExampleType,
    HousingCompanyNode,
    HousingCompanyType,
    OwnershipType,
    OwnerType,
    People,
    PlainObjectType,
    PostalCodeType,
    PropertyManagerNode,
    PropertyManagerType,
    ProteinType,
    RealEstateNode,
    RealEstateType,
    SaleType,
    TagType,
)

if TYPE_CHECKING:
    from query_optimizer.typing import GQLInfo, Iterable, Union


class Query(graphene.ObjectType):
    node = relay.Node.Field()

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

    def resolve_all_apartments(root: None, info: GQLInfo, **kwargs) -> models.QuerySet[Apartment]:
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

    def resolve_housing_company_by_name(root: None, info: GQLInfo, name: str) -> models.QuerySet[HousingCompany]:
        get_field_selections(info)
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

    def resolve_all_people(root: None, info: GQLInfo) -> Iterable[Union[Developer, PropertyManager, Owner]]:
        developers = optimize(Developer.objects.all(), info)
        property_managers = optimize(PropertyManager.objects.all(), info)
        owners = optimize(Owner.objects.all(), info)
        return itertools.chain(developers, property_managers, owners)

    all_tags = DjangoListField(TagType)
    all_content_types = DjangoListField(ContentTypeType)

    # --------------------------------------------------------------------

    proteins = DjangoListField(ProteinType)

    # --------------------------------------------------------------------

    example = graphene.Field(ExampleType, pk=graphene.Int(required=True))
    examples = DjangoListField(ExampleType)

    def resolve_example(root: None, info: GQLInfo, pk: int | None = None):
        return optimize(Example.objects.filter(pk=pk), info).first()

    # --------------------------------------------------------------------

    debug = graphene.Field(DjangoDebug, name="_debug")

    # --------------------------------------------------------------------

    plain = graphene.Field(PlainObjectType)

    def resolve_plain(root, info: GQLInfo) -> dict[str, str]:
        get_field_selections(info)
        return {
            "foo": "1",
            "bar": {
                "x": 1,
            },
        }


schema = graphene.Schema(query=Query)
