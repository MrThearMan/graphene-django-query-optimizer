# ruff: noqa: S311

import random
import string
from itertools import cycle

from django.core.management.base import BaseCommand, CommandParser
from faker import Faker

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

faker = Faker(locale="en_US")


class Command(BaseCommand):
    help = "Create test data."  # noqa: A003

    def add_arguments(self, parser: CommandParser) -> None:
        pass

    def handle(self, *args, **options) -> None:  # noqa: ARG002, ANN002, ANN003
        create_test_data()


def create_test_data() -> None:
    postal_codes = create_postal_codes()
    developers = create_developers()
    property_managers = create_property_managers()
    housing_companies = create_housing_companies(postal_codes, developers, property_managers)
    real_estates = create_real_estates(housing_companies)
    buildings = create_buildings(real_estates)
    apartments = create_apartments(buildings)
    sales = create_sales(apartments)
    owners = create_owners()
    create_ownerships(owners, sales)


def create_postal_codes() -> list[PostalCode]:
    postal_codes: list[PostalCode] = [
        PostalCode(
            code=f"{i}".zfill(5),
        )
        for i in range(1, 100_000)
    ]

    return PostalCode.objects.bulk_create(postal_codes)


def create_developers(*, number: int = 10) -> list[Developer]:
    developers: list[Developer] = [
        Developer(
            name=faker.name(),
            description=faker.sentence(),
        )
        for _ in range(number)
    ]

    return Developer.objects.bulk_create(developers)


def create_property_managers(*, number: int = 10) -> list[PropertyManager]:
    property_managers: list[PropertyManager] = [
        PropertyManager(
            name=faker.name(),
            email=faker.email(),
        )
        for _ in range(number)
    ]

    return PropertyManager.objects.bulk_create(property_managers)


def create_housing_companies(
    postal_codes: list[PostalCode],
    developers: list[Developer],
    property_managers: list[PropertyManager],
    *,
    number: int = 20,
) -> list[HousingCompany]:
    developers_loop = cycle(developers)
    property_managers_loop = cycle(property_managers)

    housing_companies: list[HousingCompany] = [
        HousingCompany(
            name=faker.company(),
            street_address=faker.street_name(),
            postal_code=random.choice(postal_codes),
            city=faker.city(),
            developer=next(developers_loop),
            property_manager=next(property_managers_loop),
        )
        for _ in range(number)
    ]

    return HousingCompany.objects.bulk_create(housing_companies)


def create_real_estates(housing_companies: list[HousingCompany]) -> list[RealEstate]:
    real_estates: list[RealEstate] = [
        RealEstate(
            name="".join(faker.words(3)),
            surface_area=random.randint(1, 200),
            housing_company=housing_company,
        )
        for housing_company in housing_companies
    ]

    return RealEstate.objects.bulk_create(real_estates)


def create_buildings(real_estates: list[RealEstate]) -> list[Building]:
    buildings: list[Building] = [
        Building(
            name="".join(faker.words(3)),
            street_address=faker.street_name(),
            real_estate=real_estate,
        )
        for real_estate in real_estates
    ]

    return Building.objects.bulk_create(buildings)


def create_apartments(buildings: list[Building]) -> list[Apartment]:
    apartments: list[Apartment] = [
        Apartment(
            completion_date=faker.date_between(),
            street_address=faker.street_name(),
            stair=random.choice(string.ascii_uppercase),
            floor=random.choice([None, 1, 2, 3, 4]),
            apartment_number=random.randint(1, 100),
            shares_start=random.randint(1, 1000),
            shares_end=random.randint(1, 1000),
            surface_area=random.randint(1, 200),
            rooms=random.randint(1, 10),
            building=building,
        )
        for building in buildings
        for _ in range(random.randint(1, 3))
    ]

    return Apartment.objects.bulk_create(apartments)


def create_sales(apartments: list[Apartment]) -> list[Sale]:
    sales: list[Sale] = [
        Sale(
            apartment=apartment,
            purchase_date=faker.date_between(),
            purchase_price=random.randint(1, 1_000_000),
        )
        for apartment in apartments
        for _ in range(random.randint(1, 3))
    ]

    return Sale.objects.bulk_create(sales)


def create_owners(*, number: int = 30) -> list[Owner]:
    owners: list[Owner] = [
        Owner(
            name=faker.name(),
            identifier=faker.text(max_nb_chars=11),
            email=faker.email(),
            phone=faker.phone_number(),
        )
        for _ in range(number)
    ]

    return Owner.objects.bulk_create(owners)


def create_ownerships(owners: list[Owner], sales: list[Sale]) -> list[Ownership]:
    owners_loop = cycle(owners)

    ownerships: list[Ownership] = [
        Ownership(
            owner=next(owners_loop),
            sale=sale,
            percentage=random.randint(1, 100),
        )
        for sale in sales
        for _ in range(random.randint(1, 3))
    ]

    return Ownership.objects.bulk_create(ownerships)
