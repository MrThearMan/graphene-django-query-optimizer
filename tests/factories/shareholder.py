from factory import fuzzy

from example_project.app.models import Shareholder

from ._base import GenericDjangoModelFactory, ManyToManyFactory


class ShareholderFactory(GenericDjangoModelFactory[Shareholder]):
    class Meta:
        model = Shareholder
        django_get_or_create = ["name"]

    name = fuzzy.FuzzyText()
    share = fuzzy.FuzzyDecimal(0, 100)
    housing_companies = ManyToManyFactory("tests.factories.housing_company.HousingCompanyFactory")
