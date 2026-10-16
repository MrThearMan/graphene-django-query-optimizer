from __future__ import annotations

from factory import fuzzy

from example_project.undine_port.models import TaskStep

from ._base import ForeignKeyFactory, GenericDjangoModelFactory, UndineFaker


class TaskStepFactory(GenericDjangoModelFactory[TaskStep]):
    class Meta:
        model = TaskStep

    name = UndineFaker("name")
    done = fuzzy.FuzzyChoice([True, False])

    task = ForeignKeyFactory("tests.undine_port.factories.TaskFactory")
