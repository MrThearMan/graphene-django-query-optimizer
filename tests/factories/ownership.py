from factory import fuzzy

from tests.example.models import Ownership

from ._base import GenericDjangoModelFactory, NullableSubFactory


class OwnershipFactory(GenericDjangoModelFactory[Ownership]):
    class Meta:
        model = Ownership

    percentage = fuzzy.FuzzyInteger(0, 100)

    owner = NullableSubFactory("tests.factories.owner.OwnerFactory")
    sale = NullableSubFactory("tests.factories.sale.SaleFactory")
