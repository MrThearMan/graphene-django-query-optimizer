from factory import fuzzy

from example_project.app.models import Employee, EmployeeRole

from ._base import GenericDjangoModelFactory, ManyToManyFactory


class EmployeeFactory(GenericDjangoModelFactory[Employee]):
    class Meta:
        model = Employee
        django_get_or_create = ["name"]

    name = fuzzy.FuzzyText()
    role = fuzzy.FuzzyChoice(EmployeeRole.values)

    developers = ManyToManyFactory("tests.factories.developer.DeveloperFactory")
