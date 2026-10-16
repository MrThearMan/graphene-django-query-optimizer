from __future__ import annotations

import factory

from example_project.undine_port.models import (
    Example,
    ExampleFFK,
    ExampleFMTM,
    ExampleFOTO,
    ExampleGeneric,
    ExampleRFK,
    ExampleRMTM,
    ExampleROTO,
    NestedExampleFFK,
    NestedExampleFMTM,
    NestedExampleFOTO,
    NestedExampleRFK,
    NestedExampleRMTM,
    NestedExampleROTO,
)

from . import _base as base

__all__ = [
    "ExampleFFKFactory",
    "ExampleFMTMFactory",
    "ExampleFOTOFactory",
    "ExampleFactory",
    "ExampleGenericFactory",
    "ExampleRFKFactory",
    "ExampleRMTMFactory",
    "ExampleROTOFactory",
    "NestedExampleFFKFactory",
    "NestedExampleFMTMFactory",
    "NestedExampleFOTOFactory",
    "NestedExampleRFKFactory",
    "NestedExampleRMTMFactory",
    "NestedExampleROTOFactory",
]


class ExampleGenericFactory(base.GenericDjangoModelFactory[ExampleGeneric]):
    class Meta:
        model = ExampleGeneric
        django_get_or_create = ["name"]

    name = factory.Sequence(str)


# --------------------------------------------------------------------


class ExampleFactory(base.GenericDjangoModelFactory[Example]):
    class Meta:
        model = Example
        django_get_or_create = ["name"]

    name = factory.Sequence(str)

    symmetrical_field = base.ManyToManyFactory(lambda: ExampleFactory)

    generic = base.ReverseForeignKeyFactory(lambda: ExampleGenericFactory)

    example_foto = base.ForwardOneToOneFactory(lambda: ExampleFOTOFactory)
    example_ffk = base.ForeignKeyFactory(lambda: ExampleFFKFactory)
    example_fmtm_set = base.ManyToManyFactory(lambda: ExampleFMTMFactory)

    example_roto = base.ReverseOneToOneFactory(lambda: ExampleROTOFactory)
    example_rfk_set = base.ReverseForeignKeyFactory(lambda: ExampleRFKFactory)
    example_rmtm_set = base.ManyToManyFactory(lambda: ExampleRMTMFactory)


# --------------------------------------------------------------------


class ExampleFOTOFactory(base.GenericDjangoModelFactory[ExampleFOTO]):
    class Meta:
        model = ExampleFOTO
        django_get_or_create = ["name"]

    name = factory.Sequence(str)

    example = base.ReverseOneToOneFactory(lambda: ExampleFactory)

    example_foto = base.ForwardOneToOneFactory(lambda: NestedExampleFOTOFactory)
    example_ffk = base.ForeignKeyFactory(lambda: NestedExampleFFKFactory)
    example_fmtm_set = base.ManyToManyFactory(lambda: NestedExampleFMTMFactory)

    example_roto = base.ReverseOneToOneFactory(lambda: NestedExampleROTOFactory)
    example_rfk_set = base.ReverseForeignKeyFactory(lambda: NestedExampleRFKFactory)
    example_rmtm_set = base.ManyToManyFactory(lambda: NestedExampleRMTMFactory)


class ExampleFFKFactory(base.GenericDjangoModelFactory[ExampleFFK]):
    class Meta:
        model = ExampleFFK
        django_get_or_create = ["name"]

    name = factory.Sequence(str)

    examples = base.ReverseForeignKeyFactory(lambda: ExampleFactory)

    example_foto = base.ForwardOneToOneFactory(lambda: NestedExampleFOTOFactory)
    example_ffk = base.ForeignKeyFactory(lambda: NestedExampleFFKFactory)
    example_fmtm_set = base.ManyToManyFactory(lambda: NestedExampleFMTMFactory)

    example_roto = base.ReverseOneToOneFactory(lambda: NestedExampleROTOFactory)
    example_rfk_set = base.ReverseForeignKeyFactory(lambda: NestedExampleRFKFactory)
    example_rmtm_set = base.ManyToManyFactory(lambda: NestedExampleRMTMFactory)


class ExampleFMTMFactory(base.GenericDjangoModelFactory[ExampleFMTM]):
    class Meta:
        model = ExampleFMTM
        django_get_or_create = ["name"]

    name = factory.Sequence(str)

    examples = base.ManyToManyFactory(lambda: ExampleFactory)

    example_foto = base.ForwardOneToOneFactory(lambda: NestedExampleFOTOFactory)
    example_ffk = base.ForeignKeyFactory(lambda: NestedExampleFFKFactory)
    example_fmtm_set = base.ManyToManyFactory(lambda: NestedExampleFMTMFactory)

    example_roto = base.ReverseOneToOneFactory(lambda: NestedExampleROTOFactory)
    example_rfk_set = base.ReverseForeignKeyFactory(lambda: NestedExampleRFKFactory)
    example_rmtm_set = base.ManyToManyFactory(lambda: NestedExampleRMTMFactory)


# --------------------------------------------------------------------


class ExampleROTOFactory(base.GenericDjangoModelFactory[ExampleROTO]):
    class Meta:
        model = ExampleROTO
        django_get_or_create = ["name"]

    name = factory.Sequence(str)

    example = base.ForwardOneToOneFactory(lambda: ExampleFactory)

    example_foto = base.ForwardOneToOneFactory(lambda: NestedExampleFOTOFactory)
    example_ffk = base.ForeignKeyFactory(lambda: NestedExampleFFKFactory)
    example_fmtm_set = base.ManyToManyFactory(lambda: NestedExampleFMTMFactory)

    example_roto = base.ReverseOneToOneFactory(lambda: NestedExampleROTOFactory)
    example_rfk_set = base.ReverseForeignKeyFactory(lambda: NestedExampleRFKFactory)
    example_rmtm_set = base.ManyToManyFactory(lambda: NestedExampleRMTMFactory)


class ExampleRFKFactory(base.GenericDjangoModelFactory[ExampleRFK]):
    class Meta:
        model = ExampleRFK
        django_get_or_create = ["name"]

    name = factory.Sequence(str)

    example = base.ForeignKeyFactory(lambda: ExampleFactory)

    example_foto = base.ForwardOneToOneFactory(lambda: NestedExampleFOTOFactory)
    example_ffk = base.ForeignKeyFactory(lambda: NestedExampleFFKFactory)
    example_fmtm_set = base.ManyToManyFactory(lambda: NestedExampleFMTMFactory)

    example_roto = base.ReverseOneToOneFactory(lambda: NestedExampleROTOFactory)
    example_rfk_set = base.ReverseForeignKeyFactory(lambda: NestedExampleRFKFactory)
    example_rmtm_set = base.ManyToManyFactory(lambda: NestedExampleRMTMFactory)


class ExampleRMTMFactory(base.GenericDjangoModelFactory[ExampleRMTM]):
    class Meta:
        model = ExampleRMTM
        django_get_or_create = ["name"]

    name = factory.Sequence(str)

    examples = base.ManyToManyFactory(lambda: ExampleFactory)

    example_foto = base.ForwardOneToOneFactory(lambda: NestedExampleFOTOFactory)
    example_ffk = base.ForeignKeyFactory(lambda: NestedExampleFFKFactory)
    example_fmtm_set = base.ManyToManyFactory(lambda: NestedExampleFMTMFactory)

    example_roto = base.ReverseOneToOneFactory(lambda: NestedExampleROTOFactory)
    example_rfk_set = base.ReverseForeignKeyFactory(lambda: NestedExampleRFKFactory)
    example_rmtm_set = base.ManyToManyFactory(lambda: NestedExampleRMTMFactory)


# --------------------------------------------------------------------


class NestedExampleFOTOFactory(base.GenericDjangoModelFactory[NestedExampleFOTO]):
    class Meta:
        model = NestedExampleFOTO
        django_get_or_create = ["name"]

    name = factory.Sequence(str)

    example_foto = base.ReverseOneToOneFactory(lambda: ExampleFOTOFactory)
    example_ffk = base.ReverseOneToOneFactory(lambda: ExampleFFKFactory)
    example_fmtm = base.ReverseOneToOneFactory(lambda: ExampleFMTMFactory)

    example_roto = base.ReverseOneToOneFactory(lambda: ExampleROTOFactory)
    example_rfk = base.ReverseOneToOneFactory(lambda: ExampleRFKFactory)
    example_rmtm = base.ReverseOneToOneFactory(lambda: ExampleRMTMFactory)


class NestedExampleFFKFactory(base.GenericDjangoModelFactory[NestedExampleFFK]):
    class Meta:
        model = NestedExampleFFK
        django_get_or_create = ["name"]

    name = factory.Sequence(str)

    example_foto_set = base.ReverseForeignKeyFactory(lambda: ExampleFOTOFactory)
    example_ffk_set = base.ReverseForeignKeyFactory(lambda: ExampleFFKFactory)
    example_fmtm_set = base.ReverseForeignKeyFactory(lambda: ExampleFMTMFactory)

    example_roto_set = base.ReverseForeignKeyFactory(lambda: ExampleROTOFactory)
    example_rfk_set = base.ReverseForeignKeyFactory(lambda: ExampleRFKFactory)
    example_rmtm_set = base.ReverseForeignKeyFactory(lambda: ExampleRMTMFactory)


class NestedExampleFMTMFactory(base.GenericDjangoModelFactory[NestedExampleFMTM]):
    class Meta:
        model = NestedExampleFMTM
        django_get_or_create = ["name"]

    name = factory.Sequence(str)

    example_foto_set = base.ManyToManyFactory(lambda: ExampleFOTOFactory)
    example_ffk_set = base.ManyToManyFactory(lambda: ExampleFFKFactory)
    example_fmtm_set = base.ManyToManyFactory(lambda: ExampleFMTMFactory)

    example_roto_set = base.ManyToManyFactory(lambda: ExampleROTOFactory)
    example_rfk_set = base.ManyToManyFactory(lambda: ExampleRFKFactory)
    example_rmtm_set = base.ManyToManyFactory(lambda: ExampleRMTMFactory)


# --------------------------------------------------------------------


class NestedExampleROTOFactory(base.GenericDjangoModelFactory[NestedExampleROTO]):
    class Meta:
        model = NestedExampleROTO
        django_get_or_create = ["name"]

    name = factory.Sequence(str)

    example_foto = base.ForwardOneToOneFactory(lambda: ExampleFOTOFactory)
    example_ffk = base.ForwardOneToOneFactory(lambda: ExampleFFKFactory)
    example_fmtm = base.ForwardOneToOneFactory(lambda: ExampleFMTMFactory)

    example_roto = base.ForwardOneToOneFactory(lambda: ExampleROTOFactory)
    example_rfk = base.ForwardOneToOneFactory(lambda: ExampleRFKFactory)
    example_rmtm = base.ForwardOneToOneFactory(lambda: ExampleRMTMFactory)


class NestedExampleRFKFactory(base.GenericDjangoModelFactory[NestedExampleRFK]):
    class Meta:
        model = NestedExampleRFK
        django_get_or_create = ["name"]

    name = factory.Sequence(str)

    example_foto = base.ForeignKeyFactory(lambda: ExampleFOTOFactory)
    example_ffk = base.ForeignKeyFactory(lambda: ExampleFFKFactory)
    example_fmtm = base.ForeignKeyFactory(lambda: ExampleFMTMFactory)

    example_roto = base.ForeignKeyFactory(lambda: ExampleROTOFactory)
    example_rfk = base.ForeignKeyFactory(lambda: ExampleRFKFactory)
    example_rmtm = base.ForeignKeyFactory(lambda: ExampleRMTMFactory)


class NestedExampleRMTMFactory(base.GenericDjangoModelFactory[NestedExampleRMTM]):
    class Meta:
        model = NestedExampleRMTM
        django_get_or_create = ["name"]

    name = factory.Sequence(str)

    example_foto_set = base.ManyToManyFactory(lambda: ExampleFOTOFactory)
    example_ffk_set = base.ManyToManyFactory(lambda: ExampleFFKFactory)
    example_fmtm_set = base.ManyToManyFactory(lambda: ExampleFMTMFactory)

    example_roto_set = base.ManyToManyFactory(lambda: ExampleROTOFactory)
    example_rfk_set = base.ManyToManyFactory(lambda: ExampleRFKFactory)
    example_rmtm_set = base.ManyToManyFactory(lambda: ExampleRMTMFactory)


# --------------------------------------------------------------------
