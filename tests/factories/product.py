from factory import fuzzy

from example_project.app.models import Product

from ._base import GenericDjangoModelFactory, ManyToManyFactory, OneToManyFactory


class ProductFactory(GenericDjangoModelFactory[Product]):
    class Meta:
        model = Product
        django_get_or_create = ["name"]

    name = fuzzy.FuzzyText()
    similar = ManyToManyFactory("tests.factories.product.ProductFactory")

    images = OneToManyFactory("tests.factories.product_image.ProductImageFactory")
