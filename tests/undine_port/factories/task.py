from __future__ import annotations

import datetime
import random
import uuid

from factory import LazyFunction, fuzzy

from example_project.undine_port.models import Task, TaskTypeChoices

from ._base import (
    ForeignKeyFactory,
    ForwardOneToOneFactory,
    GenericDjangoModelFactory,
    ManyToManyFactory,
    ReverseForeignKeyFactory,
    ReverseOneToOneFactory,
    UndineFaker,
)


class TaskFactory(GenericDjangoModelFactory[Task]):
    class Meta:
        model = Task

    name = UndineFaker("name")
    type = fuzzy.FuzzyChoice(TaskTypeChoices.values)
    created_at = LazyFunction(datetime.datetime.now)
    done = False
    due_by = fuzzy.FuzzyDate(datetime.date(2020, 1, 1), datetime.date(2030, 1, 1))
    check_time = LazyFunction(lambda: datetime.time(hour=random.randint(0, 23)))  # noqa: S311
    points = fuzzy.FuzzyInteger(0, 100)
    progress = 0
    worked_hours = LazyFunction(lambda: datetime.timedelta(seconds=random.randint(0, 1000)))  # noqa: S311
    contact_email = UndineFaker("email")
    demo_url = UndineFaker("url")
    external_uuid = LazyFunction(uuid.uuid4)
    extra_data = None
    image = None
    attachment = None

    related_tasks = ManyToManyFactory("tests.undine_port.factories.TaskFactory")

    request = ForwardOneToOneFactory("tests.undine_port.factories.ServiceRequestFactory")
    project = ForeignKeyFactory("tests.undine_port.factories.ProjectFactory")
    assignees = ManyToManyFactory("tests.undine_port.factories.PersonFactory")

    result = ReverseOneToOneFactory("tests.undine_port.factories.TaskResultFactory")
    objective = ReverseOneToOneFactory("tests.undine_port.factories.TaskObjectiveFactory")
    steps = ReverseForeignKeyFactory("tests.undine_port.factories.TaskStepFactory")
    acceptancecriteria_set = ReverseForeignKeyFactory("tests.undine_port.factories.AcceptanceCriteriaFactory")
    reports = ManyToManyFactory("tests.undine_port.factories.ReportFactory")

    comments = ReverseForeignKeyFactory("tests.undine_port.factories.CommentFactory")
