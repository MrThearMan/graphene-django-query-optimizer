from factory import Faker, SubFactory

from example_project.app.models import ProductImage

from ._base import GenericDjangoModelFactory


class ProductImageFactory(GenericDjangoModelFactory[ProductImage]):
    class Meta:
        model = ProductImage
        django_get_or_create = ["image"]

    image = Faker("image_url")

    product = SubFactory("tests.factories.product_image.ProductFactory")
