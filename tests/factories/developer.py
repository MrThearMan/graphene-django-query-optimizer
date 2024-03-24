from factory import fuzzy

from tests.example.models import Developer

from ._base import GenericDjangoModelFactory, ManyToManyFactory


class DeveloperFactory(GenericDjangoModelFactory[Developer]):
    class Meta:
        model = Developer
        django_get_or_create = ["name"]

    name = fuzzy.FuzzyText()
    description = fuzzy.FuzzyText()
    housingcompany_set = ManyToManyFactory("tests.factories.housing_company.HousingCompanyFactory")
