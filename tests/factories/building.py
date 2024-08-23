from factory import fuzzy

from example_project.app.models import Building

from ._base import GenericDjangoModelFactory, NullableSubFactory, OneToManyFactory


class BuildingFactory(GenericDjangoModelFactory[Building]):
    class Meta:
        model = Building
        django_get_or_create = ["name"]

    name = fuzzy.FuzzyText()
    street_address = fuzzy.FuzzyText()
    real_estate = NullableSubFactory("tests.factories.real_estate.RealEstateFactory")
    apartments = OneToManyFactory("tests.factories.apartment.ApartmentFactory")
