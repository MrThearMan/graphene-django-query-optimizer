import factory
from factory import fuzzy

from example_project.app.models import PropertyManager

from ._base import GenericDjangoModelFactory, OneToManyFactory


class PropertyManagerFactory(GenericDjangoModelFactory[PropertyManager]):
    class Meta:
        model = PropertyManager
        django_get_or_create = ["name"]

    name = fuzzy.FuzzyText()
    email = factory.Faker("email")
    housing_companies = OneToManyFactory("tests.factories.housing_company.HousingCompanyFactory")
