import factory

from tests.example.models import (
    Example,
    ForwardManyToMany,
    ForwardManyToManyForRelated,
    ForwardManyToOne,
    ForwardManyToOneForRelated,
    ForwardOneToOne,
    ForwardOneToOneForRelated,
    ReverseManyToMany,
    ReverseManyToManyToForwardManyToMany,
    ReverseManyToManyToForwardManyToOne,
    ReverseManyToManyToForwardOneToOne,
    ReverseManyToManyToReverseManyToMany,
    ReverseManyToManyToReverseOneToMany,
    ReverseManyToManyToReverseOneToOne,
    ReverseOneToMany,
    ReverseOneToManyToForwardManyToMany,
    ReverseOneToManyToForwardManyToOne,
    ReverseOneToManyToForwardOneToOne,
    ReverseOneToManyToReverseManyToMany,
    ReverseOneToManyToReverseOneToMany,
    ReverseOneToManyToReverseOneToOne,
    ReverseOneToOne,
    ReverseOneToOneToForwardManyToMany,
    ReverseOneToOneToForwardManyToOne,
    ReverseOneToOneToForwardOneToOne,
    ReverseOneToOneToReverseManyToMany,
    ReverseOneToOneToReverseOneToMany,
    ReverseOneToOneToReverseOneToOne,
)

from ._base import (
    GenericDjangoModelFactory,
    ManyToManyFactory,
    NullableSubFactory,
    OneToManyFactory,
    ReverseSubFactory,
)

__all__ = [
    "ExampleFactory",
    "ForwardManyToManyFactory",
    "ForwardManyToManyForRelatedFactory",
    "ForwardManyToOneFactory",
    "ForwardManyToOneForRelatedFactory",
    "ForwardOneToOneFactory",
    "ForwardOneToOneForRelatedFactory",
    "ReverseManyToManyFactory",
    "ReverseManyToManyToForwardManyToManyFactory",
    "ReverseManyToManyToForwardManyToOneFactory",
    "ReverseManyToManyToForwardOneToOneFactory",
    "ReverseManyToManyToReverseManyToManyFactory",
    "ReverseManyToManyToReverseOneToManyFactory",
    "ReverseManyToManyToReverseOneToOneFactory",
    "ReverseOneToManyFactory",
    "ReverseOneToManyToForwardManyToManyFactory",
    "ReverseOneToManyToForwardManyToOneFactory",
    "ReverseOneToManyToForwardOneToOneFactory",
    "ReverseOneToManyToReverseManyToManyFactory",
    "ReverseOneToManyToReverseOneToManyFactory",
    "ReverseOneToManyToReverseOneToOneFactory",
    "ReverseOneToOneFactory",
    "ReverseOneToOneToForwardManyToManyFactory",
    "ReverseOneToOneToForwardManyToOneFactory",
    "ReverseOneToOneToForwardOneToOneFactory",
    "ReverseOneToOneToReverseManyToManyFactory",
    "ReverseOneToOneToReverseOneToManyFactory",
    "ReverseOneToOneToReverseOneToOneFactory",
]


class ExampleFactory(GenericDjangoModelFactory[Example]):
    class Meta:
        model = Example
        django_get_or_create = ["name"]

    name = factory.Sequence(lambda n: str(n))

    symmetrical_field = ManyToManyFactory(lambda: ExampleFactory)

    forward_one_to_one_field = NullableSubFactory(lambda: ForwardOneToOneFactory)
    forward_many_to_one_field = NullableSubFactory(lambda: ForwardManyToOneFactory)
    forward_many_to_many_fields = ManyToManyFactory(lambda: ForwardManyToManyFactory)

    reverse_one_to_one_rel = ReverseSubFactory(lambda: ReverseOneToOneFactory)
    reverse_one_to_many_rels = OneToManyFactory(lambda: ReverseOneToManyFactory)
    reverse_many_to_many_rels = ManyToManyFactory(lambda: ReverseManyToManyFactory)

    named_relation = NullableSubFactory("tests.factories.housing_company.HousingCompanyFactory")


# --------------------------------------------------------------------


class ForwardOneToOneFactory(GenericDjangoModelFactory[ForwardOneToOne]):
    class Meta:
        model = ForwardOneToOne
        django_get_or_create = ["name"]

    name = factory.Sequence(lambda n: str(n))

    example_rel = ReverseSubFactory(lambda: ExampleFactory)

    forward_one_to_one_field = NullableSubFactory(lambda: ForwardOneToOneForRelatedFactory)
    forward_many_to_one_field = NullableSubFactory(lambda: ForwardManyToOneForRelatedFactory)
    forward_many_to_many_fields = ManyToManyFactory(lambda: ForwardManyToManyForRelatedFactory)

    reverse_one_to_one_rel = ReverseSubFactory(lambda: ReverseOneToOneToForwardOneToOneFactory)
    reverse_one_to_many_rels = OneToManyFactory(lambda: ReverseOneToManyToForwardOneToOneFactory)
    reverse_many_to_many_rels = ManyToManyFactory(lambda: ReverseManyToManyToForwardOneToOneFactory)


class ForwardManyToOneFactory(GenericDjangoModelFactory[ForwardManyToOne]):
    class Meta:
        model = ForwardManyToOne
        django_get_or_create = ["name"]

    name = factory.Sequence(lambda n: str(n))

    example_rels = OneToManyFactory(lambda: ExampleFactory)

    forward_one_to_one_field = NullableSubFactory(lambda: ForwardOneToOneForRelatedFactory)
    forward_many_to_one_field = NullableSubFactory(lambda: ForwardManyToOneForRelatedFactory)
    forward_many_to_many_fields = ManyToManyFactory(lambda: ForwardManyToManyForRelatedFactory)

    reverse_one_to_one_rel = ReverseSubFactory(lambda: ReverseOneToOneToForwardManyToOneFactory)
    reverse_one_to_many_rels = OneToManyFactory(lambda: ReverseOneToManyToForwardManyToOneFactory)
    reverse_many_to_many_rels = ManyToManyFactory(lambda: ReverseManyToManyToForwardManyToOneFactory)


class ForwardManyToManyFactory(GenericDjangoModelFactory[ForwardManyToMany]):
    class Meta:
        model = ForwardManyToMany
        django_get_or_create = ["name"]

    name = factory.Sequence(lambda n: str(n))

    example_rels = ManyToManyFactory(lambda: ExampleFactory)

    forward_one_to_one_field = NullableSubFactory(lambda: ForwardOneToOneForRelatedFactory)
    forward_many_to_one_field = NullableSubFactory(lambda: ForwardManyToOneForRelatedFactory)
    forward_many_to_many_fields = ManyToManyFactory(lambda: ForwardManyToManyForRelatedFactory)

    reverse_one_to_one_rel = ReverseSubFactory(lambda: ReverseOneToOneToForwardManyToManyFactory)
    reverse_one_to_many_rels = OneToManyFactory(lambda: ReverseOneToManyToForwardManyToManyFactory)
    reverse_many_to_many_rels = ManyToManyFactory(lambda: ReverseManyToManyToForwardManyToManyFactory)


# --------------------------------------------------------------------


class ReverseOneToOneFactory(GenericDjangoModelFactory[ReverseOneToOne]):
    class Meta:
        model = ReverseOneToOne
        django_get_or_create = ["name"]

    name = factory.Sequence(lambda n: str(n))

    example_field = NullableSubFactory(lambda: ExampleFactory)

    forward_one_to_one_field = NullableSubFactory(lambda: ForwardOneToOneForRelatedFactory)
    forward_many_to_one_field = NullableSubFactory(lambda: ForwardManyToOneForRelatedFactory)
    forward_many_to_many_fields = ManyToManyFactory(lambda: ForwardManyToManyForRelatedFactory)

    reverse_one_to_one_rel = ReverseSubFactory(lambda: ReverseOneToOneToReverseOneToOneFactory)
    reverse_one_to_many_rels = OneToManyFactory(lambda: ReverseOneToManyToReverseOneToOneFactory)
    reverse_many_to_many_rels = ManyToManyFactory(lambda: ReverseManyToManyToReverseOneToOneFactory)


class ReverseOneToManyFactory(GenericDjangoModelFactory[ReverseOneToMany]):
    class Meta:
        model = ReverseOneToMany
        django_get_or_create = ["name"]

    name = factory.Sequence(lambda n: str(n))

    example_field = NullableSubFactory(lambda: ExampleFactory)

    forward_one_to_one_field = NullableSubFactory(lambda: ForwardOneToOneForRelatedFactory)
    forward_many_to_one_field = NullableSubFactory(lambda: ForwardManyToOneForRelatedFactory)
    forward_many_to_many_fields = ManyToManyFactory(lambda: ForwardManyToManyForRelatedFactory)

    reverse_one_to_one_rel = ReverseSubFactory(lambda: ReverseOneToOneToReverseOneToManyFactory)
    reverse_one_to_many_rels = OneToManyFactory(lambda: ReverseOneToManyToReverseOneToManyFactory)
    reverse_many_to_many_rels = ManyToManyFactory(lambda: ReverseManyToManyToReverseOneToManyFactory)


class ReverseManyToManyFactory(GenericDjangoModelFactory[ReverseManyToMany]):
    class Meta:
        model = ReverseManyToMany
        django_get_or_create = ["name"]

    name = factory.Sequence(lambda n: str(n))

    example_fields = ManyToManyFactory(lambda: ExampleFactory)

    forward_one_to_one_field = NullableSubFactory(lambda: ForwardOneToOneForRelatedFactory)
    forward_many_to_one_field = NullableSubFactory(lambda: ForwardManyToOneForRelatedFactory)
    forward_many_to_many_fields = ManyToManyFactory(lambda: ForwardManyToManyForRelatedFactory)

    reverse_one_to_one_rel = ReverseSubFactory(lambda: ReverseOneToOneToReverseManyToManyFactory)
    reverse_one_to_many_rels = OneToManyFactory(lambda: ReverseOneToManyToReverseManyToManyFactory)
    reverse_many_to_many_rels = ManyToManyFactory(lambda: ReverseManyToManyToReverseManyToManyFactory)


# --------------------------------------------------------------------


class ForwardOneToOneForRelatedFactory(GenericDjangoModelFactory[ForwardOneToOneForRelated]):
    class Meta:
        model = ForwardOneToOneForRelated
        django_get_or_create = ["name"]

    name = factory.Sequence(lambda n: str(n))

    forward_one_to_one_rel = ReverseSubFactory(lambda: ForwardOneToOneFactory)
    forward_many_to_one_rel = ReverseSubFactory(lambda: ForwardManyToOneFactory)
    forward_many_to_many_rel = ReverseSubFactory(lambda: ForwardManyToManyFactory)

    reverse_one_to_one_rel = ReverseSubFactory(lambda: ReverseOneToOneFactory)
    reverse_one_to_many_rel = ReverseSubFactory(lambda: ReverseOneToManyFactory)
    reverse_many_to_many_rel = ReverseSubFactory(lambda: ReverseManyToManyFactory)


class ForwardManyToOneForRelatedFactory(GenericDjangoModelFactory[ForwardManyToOneForRelated]):
    class Meta:
        model = ForwardManyToOneForRelated
        django_get_or_create = ["name"]

    name = factory.Sequence(lambda n: str(n))

    forward_one_to_one_rels = OneToManyFactory(lambda: ForwardOneToOneFactory)
    forward_many_to_one_rels = OneToManyFactory(lambda: ForwardManyToOneFactory)
    forward_many_to_many_rels = OneToManyFactory(lambda: ForwardManyToManyFactory)

    reverse_one_to_one_rels = OneToManyFactory(lambda: ReverseOneToOneFactory)
    reverse_one_to_many_rels = OneToManyFactory(lambda: ReverseOneToManyFactory)
    reverse_many_to_many_rels = OneToManyFactory(lambda: ReverseManyToManyFactory)


class ForwardManyToManyForRelatedFactory(GenericDjangoModelFactory[ForwardManyToManyForRelated]):
    class Meta:
        model = ForwardManyToManyForRelated
        django_get_or_create = ["name"]

    name = factory.Sequence(lambda n: str(n))

    forward_one_to_one_rels = ManyToManyFactory(lambda: ForwardOneToOneFactory)
    forward_many_to_one_rels = ManyToManyFactory(lambda: ForwardManyToOneFactory)
    forward_many_to_many_rels = ManyToManyFactory(lambda: ForwardManyToManyFactory)

    reverse_one_to_one_rels = ManyToManyFactory(lambda: ReverseOneToOneFactory)
    reverse_one_to_many_rels = ManyToManyFactory(lambda: ReverseOneToManyFactory)
    reverse_many_to_many_rels = ManyToManyFactory(lambda: ReverseManyToManyFactory)


# --------------------------------------------------------------------


class ReverseOneToOneToForwardOneToOneFactory(GenericDjangoModelFactory[ReverseOneToOneToForwardOneToOne]):
    class Meta:
        model = ReverseOneToOneToForwardOneToOne
        django_get_or_create = ["name"]

    name = factory.Sequence(lambda n: str(n))

    forward_one_to_one_field = NullableSubFactory(lambda: ForwardOneToOneFactory)


class ReverseOneToOneToForwardManyToOneFactory(GenericDjangoModelFactory[ReverseOneToOneToForwardManyToOne]):
    class Meta:
        model = ReverseOneToOneToForwardManyToOne
        django_get_or_create = ["name"]

    name = factory.Sequence(lambda n: str(n))

    forward_many_to_one_field = NullableSubFactory(lambda: ForwardManyToOneFactory)


class ReverseOneToOneToForwardManyToManyFactory(GenericDjangoModelFactory[ReverseOneToOneToForwardManyToMany]):
    class Meta:
        model = ReverseOneToOneToForwardManyToMany
        django_get_or_create = ["name"]

    name = factory.Sequence(lambda n: str(n))

    forward_many_to_many_field = NullableSubFactory(lambda: ForwardManyToManyFactory)


# --------------------------------------------------------------------


class ReverseOneToOneToReverseOneToOneFactory(GenericDjangoModelFactory[ReverseOneToOneToReverseOneToOne]):
    class Meta:
        model = ReverseOneToOneToReverseOneToOne
        django_get_or_create = ["name"]

    name = factory.Sequence(lambda n: str(n))

    reverse_one_to_one_field = NullableSubFactory(lambda: ReverseOneToOneFactory)


class ReverseOneToOneToReverseOneToManyFactory(GenericDjangoModelFactory[ReverseOneToOneToReverseOneToMany]):
    class Meta:
        model = ReverseOneToOneToReverseOneToMany
        django_get_or_create = ["name"]

    name = factory.Sequence(lambda n: str(n))

    reverse_many_to_one_field = NullableSubFactory(lambda: ReverseOneToManyFactory)


class ReverseOneToOneToReverseManyToManyFactory(GenericDjangoModelFactory[ReverseOneToOneToReverseManyToMany]):
    class Meta:
        model = ReverseOneToOneToReverseManyToMany
        django_get_or_create = ["name"]

    name = factory.Sequence(lambda n: str(n))

    reverse_many_to_many_field = NullableSubFactory(lambda: ReverseManyToManyFactory)


# --------------------------------------------------------------------


class ReverseOneToManyToForwardOneToOneFactory(GenericDjangoModelFactory[ReverseOneToManyToForwardOneToOne]):
    class Meta:
        model = ReverseOneToManyToForwardOneToOne
        django_get_or_create = ["name"]

    name = factory.Sequence(lambda n: str(n))

    forward_one_to_one_field = NullableSubFactory(lambda: ForwardOneToOneFactory)


class ReverseOneToManyToForwardManyToOneFactory(GenericDjangoModelFactory[ReverseOneToManyToForwardManyToOne]):
    class Meta:
        model = ReverseOneToManyToForwardManyToOne
        django_get_or_create = ["name"]

    name = factory.Sequence(lambda n: str(n))

    forward_many_to_one_field = NullableSubFactory(lambda: ForwardManyToOneFactory)


class ReverseOneToManyToForwardManyToManyFactory(GenericDjangoModelFactory[ReverseOneToManyToForwardManyToMany]):
    class Meta:
        model = ReverseOneToManyToForwardManyToMany
        django_get_or_create = ["name"]

    name = factory.Sequence(lambda n: str(n))

    forward_many_to_many_field = NullableSubFactory(lambda: ForwardManyToManyFactory)


# --------------------------------------------------------------------


class ReverseOneToManyToReverseOneToOneFactory(GenericDjangoModelFactory[ReverseOneToManyToReverseOneToOne]):
    class Meta:
        model = ReverseOneToManyToReverseOneToOne
        django_get_or_create = ["name"]

    name = factory.Sequence(lambda n: str(n))

    reverse_one_to_one_field = NullableSubFactory(lambda: ReverseOneToOneFactory)


class ReverseOneToManyToReverseOneToManyFactory(GenericDjangoModelFactory[ReverseOneToManyToReverseOneToMany]):
    class Meta:
        model = ReverseOneToManyToReverseOneToMany
        django_get_or_create = ["name"]

    name = factory.Sequence(lambda n: str(n))

    reverse_many_to_one_field = NullableSubFactory(lambda: ReverseOneToManyFactory)


class ReverseOneToManyToReverseManyToManyFactory(GenericDjangoModelFactory[ReverseOneToManyToReverseManyToMany]):
    class Meta:
        model = ReverseOneToManyToReverseManyToMany
        django_get_or_create = ["name"]

    name = factory.Sequence(lambda n: str(n))

    reverse_many_to_many_field = NullableSubFactory(lambda: ReverseManyToManyFactory)


# --------------------------------------------------------------------


class ReverseManyToManyToForwardOneToOneFactory(GenericDjangoModelFactory[ReverseManyToManyToForwardOneToOne]):
    class Meta:
        model = ReverseManyToManyToForwardOneToOne
        django_get_or_create = ["name"]

    name = factory.Sequence(lambda n: str(n))

    forward_one_to_one_fields = ManyToManyFactory(lambda: ForwardOneToOneFactory)


class ReverseManyToManyToForwardManyToOneFactory(GenericDjangoModelFactory[ReverseManyToManyToForwardManyToOne]):
    class Meta:
        model = ReverseManyToManyToForwardManyToOne
        django_get_or_create = ["name"]

    name = factory.Sequence(lambda n: str(n))

    forward_many_to_one_fields = ManyToManyFactory(lambda: ForwardManyToOneFactory)


class ReverseManyToManyToForwardManyToManyFactory(GenericDjangoModelFactory[ReverseManyToManyToForwardManyToMany]):
    class Meta:
        model = ReverseManyToManyToForwardManyToMany
        django_get_or_create = ["name"]

    name = factory.Sequence(lambda n: str(n))

    forward_many_to_many_fields = ManyToManyFactory(lambda: ForwardManyToManyFactory)


# --------------------------------------------------------------------


class ReverseManyToManyToReverseOneToOneFactory(GenericDjangoModelFactory[ReverseManyToManyToReverseOneToOne]):
    class Meta:
        model = ReverseManyToManyToReverseOneToOne
        django_get_or_create = ["name"]

    name = factory.Sequence(lambda n: str(n))

    reverse_one_to_one_fields = ManyToManyFactory(lambda: ReverseOneToOneFactory)


class ReverseManyToManyToReverseOneToManyFactory(GenericDjangoModelFactory[ReverseManyToManyToReverseOneToMany]):
    class Meta:
        model = ReverseManyToManyToReverseOneToMany
        django_get_or_create = ["name"]

    name = factory.Sequence(lambda n: str(n))

    reverse_many_to_one_fields = ManyToManyFactory(lambda: ReverseOneToManyFactory)


class ReverseManyToManyToReverseManyToManyFactory(GenericDjangoModelFactory[ReverseManyToManyToReverseManyToMany]):
    class Meta:
        model = ReverseManyToManyToReverseManyToMany
        django_get_or_create = ["name"]

    name = factory.Sequence(lambda n: str(n))

    reverse_many_to_many_fields = ManyToManyFactory(lambda: ReverseManyToManyFactory)


# --------------------------------------------------------------------
