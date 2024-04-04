from typing import Any

from django.db.models import Model
from factory import fuzzy

from tests.example.models import Tag

from ._base import GenericDjangoModelFactory


class TagFactory(GenericDjangoModelFactory[Tag]):
    class Meta:
        model = Tag

    tag = fuzzy.FuzzyText()

    @classmethod
    def build(cls, content_object: Model, **kwargs: Any) -> Tag:
        return super().build(content_object=content_object, **kwargs)

    @classmethod
    def create(cls, content_object: Model, **kwargs: Any) -> Tag:
        return super().create(content_object=content_object, **kwargs)
