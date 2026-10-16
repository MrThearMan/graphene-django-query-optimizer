from __future__ import annotations

import datetime

import factory
from factory import fuzzy

from example_project.undine_port.models import Comment

from ._base import ForeignKeyFactory, GenericDjangoModelFactory


class CommentFactory(GenericDjangoModelFactory[Comment]):
    class Meta:
        model = Comment

    contents = fuzzy.FuzzyText(length=100)
    updated_at = factory.LazyFunction(datetime.datetime.now)

    commenter = ForeignKeyFactory("tests.undine_port.factories.PersonFactory")
