from __future__ import annotations

from example_project.undine_port.models import Person

from ._base import GenericDjangoModelFactory, ManyToManyFactory, ReverseForeignKeyFactory, UndineFaker


class PersonFactory(GenericDjangoModelFactory[Person]):
    class Meta:
        model = Person

    name = UndineFaker("name")
    email = UndineFaker("email", unique=True)

    comments = ReverseForeignKeyFactory("tests.undine_port.factories.CommentFactory")
    teams = ManyToManyFactory("tests.undine_port.factories.TeamFactory")
    tasks = ManyToManyFactory("tests.undine_port.factories.TaskFactory")
