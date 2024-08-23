from factory import fuzzy

from example_project.app.models import Ownership

from ._base import GenericDjangoModelFactory, NullableSubFactory


class OwnershipFactory(GenericDjangoModelFactory[Ownership]):
    class Meta:
        model = Ownership

    percentage = fuzzy.FuzzyInteger(0, 100)

    owner = NullableSubFactory("tests.factories.owner.OwnerFactory")
    sale = NullableSubFactory("tests.factories.sale.SaleFactory")
