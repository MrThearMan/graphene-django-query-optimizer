from factory import fuzzy

from example_project.app.models import RealEstate

from ._base import GenericDjangoModelFactory, NullableSubFactory, OneToManyFactory


class RealEstateFactory(GenericDjangoModelFactory[RealEstate]):
    class Meta:
        model = RealEstate
        django_get_or_create = ["name"]

    name = fuzzy.FuzzyText()
    surface_area = fuzzy.FuzzyInteger(1, 1000)
    housing_company = NullableSubFactory("tests.factories.housing_company.HousingCompanyFactory")
    building_set = OneToManyFactory("tests.factories.building.BuildingFactory")
