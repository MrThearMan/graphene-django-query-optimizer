from __future__ import annotations

from factory import fuzzy

from example_project.undine_port.models import TaskObjective

from ._base import ForwardOneToOneFactory, GenericDjangoModelFactory


class TaskObjectiveFactory(GenericDjangoModelFactory[TaskObjective]):
    class Meta:
        model = TaskObjective

    details = fuzzy.FuzzyText(length=100)

    task = ForwardOneToOneFactory("tests.undine_port.factories.TaskFactory")
