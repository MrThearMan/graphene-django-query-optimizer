from factory import fuzzy

from example_project.app.models import PostalCode

from ._base import GenericDjangoModelFactory, OneToManyFactory


class PostalCodeFactory(GenericDjangoModelFactory[PostalCode]):
    class Meta:
        model = PostalCode
        django_get_or_create = ["code"]

    code = fuzzy.FuzzyText()
    housing_companies = OneToManyFactory("tests.factories.housing_company.HousingCompanyFactory")
