from __future__ import annotations

from example_project.undine_port.models import Team

from ._base import GenericDjangoModelFactory, ManyToManyFactory, ReverseForeignKeyFactory, UndineFaker


class TeamFactory(GenericDjangoModelFactory[Team]):
    class Meta:
        model = Team

    name = UndineFaker("name")

    members = ManyToManyFactory("tests.undine_port.factories.PersonFactory")
    projects = ReverseForeignKeyFactory("tests.undine_port.factories.ProjectFactory")
