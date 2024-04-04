import random
import string
from itertools import cycle

from django.core.management import call_command
from django.core.management.base import BaseCommand, CommandParser
from faker import Faker

from tests.example.models import (
    Apartment,
    Building,
    Developer,
    Example,
    ForwardManyToMany,
    ForwardManyToManyForRelated,
    ForwardManyToOne,
    ForwardManyToOneForRelated,
    ForwardOneToOne,
    ForwardOneToOneForRelated,
    HousingCompany,
    Owner,
    Ownership,
    PostalCode,
    PropertyManager,
    RealEstate,
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
    Tag,
)

faker = Faker(locale="en_US")


class Command(BaseCommand):
    help = "Create test data."

    def add_arguments(self, parser: CommandParser) -> None:
        pass

    def handle(self, *args, **options) -> None:  # noqa: ANN002, ANN003
        create_test_data()


def create_test_data() -> None:
    clear_database()
    postal_codes = create_postal_codes()
    developers = create_developers()
    create_tags(postal_codes, developers)
    property_managers = create_property_managers()
    housing_companies = create_housing_companies(postal_codes, developers, property_managers)
    real_estates = create_real_estates(housing_companies)
    buildings = create_buildings(real_estates)
    apartments = create_apartments(buildings)
    sales = create_sales(apartments)
    owners = create_owners()
    create_ownerships(owners, sales)

    create_examples()


def clear_database() -> None:
    call_command("flush", "--noinput")


def create_postal_codes() -> list[PostalCode]:
    codes = {random.randint(1, 100_000) for _ in range(1000)}
    postal_codes: list[PostalCode] = [
        PostalCode(
            code=f"{i}".zfill(5),
        )
        for i in codes
    ]

    return PostalCode.objects.bulk_create(postal_codes)


def create_tags(postal_codes: list[PostalCode], developers: list[Developer]) -> list[Tag]:
    return [
        Tag.objects.create(
            tag=faker.word(),
            content_object=postal_code,
        )
        for postal_code in random.sample(postal_codes, k=200)
        for _ in range(2)
    ] + [
        Tag.objects.create(
            tag=faker.word(),
            content_object=developer,
        )
        for developer in developers
    ]


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
    first_choice = property_managers.copy()

    def get_manager() -> PropertyManager:
        if first_choice:  # make sure each property manager has at least one housing company
            return first_choice.pop()
        return random.choice(property_managers)

    housing_companies: list[HousingCompany] = [
        HousingCompany(
            name=faker.company(),
            street_address=faker.street_name(),
            postal_code=random.choice(postal_codes),
            city=faker.city(),
            property_manager=get_manager(),
        )
        for _ in range(number)
    ]

    housing_companies = HousingCompany.objects.bulk_create(housing_companies)
    for housing_company in housing_companies:
        housing_company.developers.add(*random.sample(developers, k=random.randint(1, 3)))

    return housing_companies


def create_real_estates(housing_companies: list[HousingCompany]) -> list[RealEstate]:
    real_estates: list[RealEstate] = [
        RealEstate(
            name="".join(faker.words(3)),
            surface_area=random.randint(1, 200),
            housing_company=housing_company,
        )
        for _ in range(2)
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


def create_examples() -> None:
    # example
    #   <-> symmetrical
    #   --> forward_one_to_one
    #       --> forward_one_to_one_for_related_field
    #       --> forward_many_to_one_for_related_field
    #       --> forward_many_to_many_for_related_fields
    #       <-- reverse_one_to_one_for_forward_one_to_one
    #       <-- reverse_many_to_one_for_forward_one_to_one
    #       <-- reverse_many_to_many_for_forward_one_to_one
    #   --> forward_many_to_one
    #       --> forward_one_to_one_for_related_field
    #       --> forward_many_to_one_for_related_field
    #       --> forward_many_to_many_for_related_fields
    #       <-- reverse_one_to_one_for_forward_many_to_one
    #       <-- reverse_many_to_one_for_forward_many_to_one
    #       <-- reverse_many_to_many_for_forward_many_to_one
    #   --> forward_many_to_many
    #       --> forward_one_to_one_for_related_field
    #       --> forward_many_to_one_for_related_field
    #       --> forward_many_to_many_for_related_fields
    #       <-- reverse_one_to_one_for_forward_many_to_many
    #       <-- reverse_many_to_one_for_forward_many_to_many
    #       <-- reverse_many_to_many_for_forward_many_to_many
    #   <-- reverse_one_to_one
    #       --> forward_one_to_one_for_related_field
    #       --> forward_many_to_one_for_related_field
    #       --> forward_many_to_many_for_related_fields
    #       <-- reverse_one_to_one_for_reverse_one_to_one
    #       <-- reverse_many_to_one_for_reverse_one_to_one
    #       <-- reverse_many_to_many_for_reverse_one_to_one
    #   <-- reverse_many_to_one
    #       --> forward_one_to_one_for_related
    #       --> forward_many_to_one_for_related
    #       --> forward_many_to_many_for_related
    #       <-- reverse_one_to_one_for_reverse_many_to_one
    #       <-- reverse_many_to_one_for_reverse_many_to_one
    #       <-- reverse_many_to_many_for_reverse_many_to_one
    #   <-- reverse_many_to_many
    #       --> forward_one_to_one_for_related
    #       --> forward_many_to_one_for_related
    #       --> forward_many_to_many_for_related
    #       <-- reverse_one_to_one_for_reverse_many_to_many
    #       <-- reverse_many_to_one_for_reverse_many_to_many
    #       <-- reverse_many_to_many_for_reverse_many_to_many

    f100 = ForwardOneToOneForRelated.objects.create(name=faker.name())
    f101 = ForwardOneToOneForRelated.objects.create(name=faker.name())
    f102 = ForwardOneToOneForRelated.objects.create(name=faker.name())
    f103 = ForwardOneToOneForRelated.objects.create(name=faker.name())
    f104 = ForwardOneToOneForRelated.objects.create(name=faker.name())
    f105 = ForwardOneToOneForRelated.objects.create(name=faker.name())
    f106 = ForwardOneToOneForRelated.objects.create(name=faker.name())
    f107 = ForwardOneToOneForRelated.objects.create(name=faker.name())

    f110 = ForwardOneToOneForRelated.objects.create(name=faker.name())
    f111 = ForwardOneToOneForRelated.objects.create(name=faker.name())
    f112 = ForwardOneToOneForRelated.objects.create(name=faker.name())
    f113 = ForwardOneToOneForRelated.objects.create(name=faker.name())
    f114 = ForwardOneToOneForRelated.objects.create(name=faker.name())
    f115 = ForwardOneToOneForRelated.objects.create(name=faker.name())
    f116 = ForwardOneToOneForRelated.objects.create(name=faker.name())

    f200 = ForwardManyToOneForRelated.objects.create(name=faker.name())
    f201 = ForwardManyToOneForRelated.objects.create(name=faker.name())

    f300 = ForwardManyToManyForRelated.objects.create(name=faker.name())
    f301 = ForwardManyToManyForRelated.objects.create(name=faker.name())
    f302 = ForwardManyToManyForRelated.objects.create(name=faker.name())

    f10 = ForwardOneToOne.objects.create(
        name=faker.name(),
        forward_one_to_one_field=f110,
        forward_many_to_one_field=f200,
    )
    f11 = ForwardOneToOne.objects.create(
        name=faker.name(),
        forward_one_to_one_field=f111,
        forward_many_to_one_field=f201,
    )
    f10.forward_many_to_many_fields.add(f300, f301)
    f11.forward_many_to_many_fields.add(f300, f302)

    f20 = ForwardManyToOne.objects.create(
        name=faker.name(),
        forward_one_to_one_field=f112,
        forward_many_to_one_field=f200,
    )
    f21 = ForwardManyToOne.objects.create(
        name=faker.name(),
        forward_one_to_one_field=f113,
        forward_many_to_one_field=f201,
    )
    f20.forward_many_to_many_fields.add(f300, f301)
    f21.forward_many_to_many_fields.add(f300, f302)

    f30 = ForwardManyToMany.objects.create(
        name=faker.name(),
        forward_one_to_one_field=f114,
        forward_many_to_one_field=f200,
    )
    f31 = ForwardManyToMany.objects.create(
        name=faker.name(),
        forward_one_to_one_field=f115,
        forward_many_to_one_field=f201,
    )
    f32 = ForwardManyToMany.objects.create(
        name=faker.name(),
        forward_one_to_one_field=f116,
        forward_many_to_one_field=f200,
    )
    f30.forward_many_to_many_fields.add(f300, f301)
    f31.forward_many_to_many_fields.add(f300, f302)
    f32.forward_many_to_many_fields.add(f301, f302)

    h = HousingCompany.objects.first()
    e1 = Example.objects.create(
        name=faker.name(),
        forward_one_to_one_field=f10,
        forward_many_to_one_field=f20,
        named_relation=h,
    )
    e1.forward_many_to_many_fields.add(f30, f31)

    e2 = Example.objects.create(
        name=faker.name(),
        forward_one_to_one_field=f11,
        forward_many_to_one_field=f21,
        named_relation=h,
    )
    e2.forward_many_to_many_fields.add(f30, f32)

    e1.symmetrical_field.add(e2)

    r10 = ReverseOneToOne.objects.create(
        name=faker.name(),
        example_field=e1,
        forward_one_to_one_field=f100,
        forward_many_to_one_field=f200,
    )
    r11 = ReverseOneToOne.objects.create(
        name=faker.name(),
        example_field=e2,
        forward_one_to_one_field=f101,
        forward_many_to_one_field=f201,
    )
    r10.forward_many_to_many_fields.add(f300, f301)
    r11.forward_many_to_many_fields.add(f300, f302)

    r20 = ReverseOneToMany.objects.create(
        name=faker.name(),
        example_field=e1,
        forward_one_to_one_field=f102,
        forward_many_to_one_field=f200,
    )
    r21 = ReverseOneToMany.objects.create(
        name=faker.name(),
        example_field=e1,
        forward_one_to_one_field=f103,
        forward_many_to_one_field=f201,
    )
    r22 = ReverseOneToMany.objects.create(
        name=faker.name(),
        example_field=e2,
        forward_one_to_one_field=f104,
        forward_many_to_one_field=f200,
    )
    r23 = ReverseOneToMany.objects.create(
        name=faker.name(),
        example_field=e2,
        forward_one_to_one_field=f105,
        forward_many_to_one_field=f201,
    )
    r20.forward_many_to_many_fields.add(f300, f301)
    r21.forward_many_to_many_fields.add(f300, f302)
    r22.forward_many_to_many_fields.add(f300, f301)
    r23.forward_many_to_many_fields.add(f300, f302)

    r30 = ReverseManyToMany.objects.create(
        name=faker.name(),
        forward_one_to_one_field=f106,
        forward_many_to_one_field=f200,
    )
    r31 = ReverseManyToMany.objects.create(
        name=faker.name(),
        forward_one_to_one_field=f107,
        forward_many_to_one_field=f201,
    )
    r30.example_fields.add(e1, e2)
    r31.example_fields.add(e1, e2)
    r30.forward_many_to_many_fields.add(f300, f301)
    r31.forward_many_to_many_fields.add(f300, f302)

    ReverseOneToOneToForwardOneToOne.objects.create(
        name=faker.name(),
        forward_one_to_one_field=f10,
    )
    ReverseOneToOneToForwardOneToOne.objects.create(
        name=faker.name(),
        forward_one_to_one_field=f11,
    )

    ReverseOneToOneToForwardManyToOne.objects.create(
        name=faker.name(),
        forward_many_to_one_field=f20,
    )
    ReverseOneToOneToForwardManyToOne.objects.create(
        name=faker.name(),
        forward_many_to_one_field=f21,
    )

    ReverseOneToOneToForwardManyToMany.objects.create(
        name=faker.name(),
        forward_many_to_many_field=f30,
    )
    ReverseOneToOneToForwardManyToMany.objects.create(
        name=faker.name(),
        forward_many_to_many_field=f31,
    )
    ReverseOneToOneToForwardManyToMany.objects.create(
        name=faker.name(),
        forward_many_to_many_field=f32,
    )

    ReverseOneToOneToReverseOneToOne.objects.create(
        name=faker.name(),
        reverse_one_to_one_field=r10,
    )
    ReverseOneToOneToReverseOneToOne.objects.create(
        name=faker.name(),
        reverse_one_to_one_field=r11,
    )

    ReverseOneToOneToReverseOneToMany.objects.create(
        name=faker.name(),
        reverse_many_to_one_field=r20,
    )
    ReverseOneToOneToReverseOneToMany.objects.create(
        name=faker.name(),
        reverse_many_to_one_field=r21,
    )

    ReverseOneToOneToReverseManyToMany.objects.create(
        name=faker.name(),
        reverse_many_to_many_field=r30,
    )
    ReverseOneToOneToReverseManyToMany.objects.create(
        name=faker.name(),
        reverse_many_to_many_field=r31,
    )

    ReverseOneToManyToForwardOneToOne.objects.create(
        name=faker.name(),
        forward_one_to_one_field=f10,
    )
    ReverseOneToManyToForwardOneToOne.objects.create(
        name=faker.name(),
        forward_one_to_one_field=f11,
    )

    ReverseOneToManyToForwardManyToOne.objects.create(
        name=faker.name(),
        forward_many_to_one_field=f20,
    )
    ReverseOneToManyToForwardManyToOne.objects.create(
        name=faker.name(),
        forward_many_to_one_field=f21,
    )

    ReverseOneToManyToForwardManyToMany.objects.create(
        name=faker.name(),
        forward_many_to_many_field=f30,
    )
    ReverseOneToManyToForwardManyToMany.objects.create(
        name=faker.name(),
        forward_many_to_many_field=f31,
    )
    ReverseOneToManyToForwardManyToMany.objects.create(
        name=faker.name(),
        forward_many_to_many_field=f32,
    )

    ReverseOneToManyToReverseOneToOne.objects.create(
        name=faker.name(),
        reverse_one_to_one_field=r10,
    )
    ReverseOneToManyToReverseOneToOne.objects.create(
        name=faker.name(),
        reverse_one_to_one_field=r11,
    )

    ReverseOneToManyToReverseOneToMany.objects.create(
        name=faker.name(),
        reverse_many_to_one_field=r20,
    )
    ReverseOneToManyToReverseOneToMany.objects.create(
        name=faker.name(),
        reverse_many_to_one_field=r21,
    )

    ReverseOneToManyToReverseManyToMany.objects.create(
        name=faker.name(),
        reverse_many_to_many_field=r30,
    )
    ReverseOneToManyToReverseManyToMany.objects.create(
        name=faker.name(),
        reverse_many_to_many_field=r31,
    )

    r30f10 = ReverseManyToManyToForwardOneToOne.objects.create(name=faker.name())
    r30f10.forward_one_to_one_fields.add(f10, f11)
    r30f11 = ReverseManyToManyToForwardOneToOne.objects.create(name=faker.name())
    r30f11.forward_one_to_one_fields.add(f10, f11)

    r30f20 = ReverseManyToManyToForwardManyToOne.objects.create(name=faker.name())
    r30f20.forward_many_to_one_fields.add(f20, f21)
    r30f21 = ReverseManyToManyToForwardManyToOne.objects.create(name=faker.name())
    r30f21.forward_many_to_one_fields.add(f20, f21)

    r30f30 = ReverseManyToManyToForwardManyToMany.objects.create(name=faker.name())
    r30f30.forward_many_to_many_fields.add(f30, f31)
    r30f31 = ReverseManyToManyToForwardManyToMany.objects.create(name=faker.name())
    r30f31.forward_many_to_many_fields.add(f30, f32)

    r30r10 = ReverseManyToManyToReverseOneToOne.objects.create(name=faker.name())
    r30r10.reverse_one_to_one_fields.add(r10, r11)
    r30r11 = ReverseManyToManyToReverseOneToOne.objects.create(name=faker.name())
    r30r11.reverse_one_to_one_fields.add(r10, r11)

    r30r20 = ReverseManyToManyToReverseOneToMany.objects.create(name=faker.name())
    r30r20.reverse_many_to_one_fields.add(r20, r21)
    r30r21 = ReverseManyToManyToReverseOneToMany.objects.create(name=faker.name())
    r30r21.reverse_many_to_one_fields.add(r20, r21)

    r30r30 = ReverseManyToManyToReverseManyToMany.objects.create(name=faker.name())
    r30r30.reverse_many_to_many_fields.add(r30, r31)
    r30r31 = ReverseManyToManyToReverseManyToMany.objects.create(name=faker.name())
    r30r31.reverse_many_to_many_fields.add(r30, r31)
