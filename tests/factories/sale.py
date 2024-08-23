import datetime

from factory import fuzzy

from example_project.app.models import Sale

from ._base import GenericDjangoModelFactory, NullableSubFactory, OneToManyFactory


class SaleFactory(GenericDjangoModelFactory[Sale]):
    class Meta:
        model = Sale

    purchase_date = fuzzy.FuzzyDate(start_date=datetime.date.fromisoformat("2020-01-01"))
    purchase_price = fuzzy.FuzzyInteger(1, 1000)
    apartment = NullableSubFactory("tests.factories.apartment.ApartmentFactory")
    ownerships = OneToManyFactory("tests.factories.ownership.OwnershipFactory")
