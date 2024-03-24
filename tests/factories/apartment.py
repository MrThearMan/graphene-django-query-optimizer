import datetime

from factory import fuzzy

from tests.example.models import Apartment

from ._base import GenericDjangoModelFactory, NullableSubFactory, OneToManyFactory


class ApartmentFactory(GenericDjangoModelFactory[Apartment]):
    class Meta:
        model = Apartment

    completion_date = fuzzy.FuzzyDate(start_date=datetime.date.fromisoformat("2020-01-01"))

    street_address = fuzzy.FuzzyText()
    stair = fuzzy.FuzzyText()
    floor = fuzzy.FuzzyInteger(low=0)
    apartment_number = fuzzy.FuzzyInteger(low=0)

    shares_start = None
    shares_end = None

    surface_area = fuzzy.FuzzyInteger(low=0)
    rooms = fuzzy.FuzzyInteger(low=0)

    building = NullableSubFactory("tests.factories.building.BuildingFactory")
    sales = OneToManyFactory("tests.factories.sale.SaleFactory")
