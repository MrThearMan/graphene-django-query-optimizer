from __future__ import annotations

import datetime

import factory
from factory import fuzzy

from example_project.undine_port.models import TaskResult

from ._base import ForwardOneToOneFactory, GenericDjangoModelFactory


class TaskResultFactory(GenericDjangoModelFactory[TaskResult]):
    class Meta:
        model = TaskResult

    details = fuzzy.FuzzyText(length=100)
    time_used = datetime.timedelta(hours=10)
    created_at = factory.LazyFunction(datetime.datetime.now)

    task = ForwardOneToOneFactory("tests.undine_port.factories.TaskFactory")
