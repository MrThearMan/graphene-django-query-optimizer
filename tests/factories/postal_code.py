from factory import fuzzy

from tests.example.models import PostalCode

from ._base import GenericDjangoModelFactory, ManyToManyFactory


class PostalCodeFactory(GenericDjangoModelFactory[PostalCode]):
    class Meta:
        model = PostalCode
        django_get_or_create = ["code"]

    code = fuzzy.FuzzyText()
    housing_companies = ManyToManyFactory("tests.factories.housing_company.HousingCompanyFactory")
