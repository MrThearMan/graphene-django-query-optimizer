from __future__ import annotations

from factory import fuzzy

from example_project.undine_port.models import AcceptanceCriteria

from ._base import ForeignKeyFactory, GenericDjangoModelFactory


class AcceptanceCriteriaFactory(GenericDjangoModelFactory[AcceptanceCriteria]):
    class Meta:
        model = AcceptanceCriteria

    details = fuzzy.FuzzyText(length=100)
    fulfilled = fuzzy.FuzzyChoice([True, False])

    task = ForeignKeyFactory("tests.undine_port.factories.TaskFactory")
