from factory import Faker, fuzzy

from tests.example.models import Owner

from ._base import GenericDjangoModelFactory, OneToManyFactory


class OwnerFactory(GenericDjangoModelFactory[Owner]):
    class Meta:
        model = Owner
        django_get_or_create = ["name"]

    name = fuzzy.FuzzyText()
    identifier = fuzzy.FuzzyText()
    email = Faker("email")
    phone = Faker("phone_number")

    ownerships = OneToManyFactory("tests.factories.ownership.OwnershipFactory")
