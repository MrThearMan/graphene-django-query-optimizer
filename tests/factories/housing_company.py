from factory import fuzzy

from example_project.app.models import HousingCompany

from ._base import GenericDjangoModelFactory, ManyToManyFactory, NullableSubFactory, OneToManyFactory


class HousingCompanyFactory(GenericDjangoModelFactory[HousingCompany]):
    class Meta:
        model = HousingCompany
        django_get_or_create = ["name"]

    name = fuzzy.FuzzyText()
    street_address = fuzzy.FuzzyText()
    postal_code = NullableSubFactory("tests.factories.postal_code.PostalCodeFactory")
    city = fuzzy.FuzzyText()
    developers = ManyToManyFactory("tests.factories.developer.DeveloperFactory")
    property_manager = NullableSubFactory("tests.factories.property_manager.PropertyManagerFactory")
    real_estates = OneToManyFactory("tests.factories.real_estate.RealEstateFactory")
