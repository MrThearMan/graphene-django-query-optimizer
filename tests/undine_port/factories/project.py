from __future__ import annotations

from factory import SubFactory

from example_project.undine_port.models import Project

from ._base import GenericDjangoModelFactory, ReverseForeignKeyFactory, UndineFaker


class ProjectFactory(GenericDjangoModelFactory[Project]):
    class Meta:
        model = Project

    name = UndineFaker("name")

    team = SubFactory("tests.undine_port.factories.TeamFactory")
    tasks = ReverseForeignKeyFactory("tests.undine_port.factories.TaskFactory")
