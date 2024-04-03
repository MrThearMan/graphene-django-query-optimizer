from collections.abc import Iterable

from django.db.models import Model
from factory import PostGeneration
from factory.base import BaseFactory
from factory.builder import BuildStep, Resolver
from factory.declarations import SubFactory
from factory.django import DjangoModelFactory
from factory.utils import import_object

from query_optimizer.typing import Any, Callable, Generic, Optional, TModel, Union

FactoryType = Union[str, type[BaseFactory], Callable[[], type[BaseFactory]]]


__all__ = [
    "GenericDjangoModelFactory",
    "ManyToManyFactory",
    "OneToManyFactory",
    "NullableSubFactory",
]


class GenericDjangoModelFactory(DjangoModelFactory, Generic[TModel]):
    @classmethod
    def build(cls: type[Generic[TModel]], **kwargs: Any) -> TModel:
        return super().build(**kwargs)

    @classmethod
    def create(cls: type[Generic[TModel]], **kwargs: Any) -> TModel:
        return super().create(**kwargs)

    @classmethod
    def build_batch(cls: type[Generic[TModel]], size: int, **kwargs: Any) -> list[TModel]:
        return super().build_batch(size, **kwargs)

    @classmethod
    def create_batch(cls: type[Generic[TModel]], size: int, **kwargs: Any) -> list[TModel]:
        return super().create_batch(size, **kwargs)


class CustomFactoryWrapper:
    def __init__(self, factory_: FactoryType) -> None:
        self.factory: Optional[type[BaseFactory]] = None
        self.callable: Optional[Callable[..., type[BaseFactory]]] = None

        if isinstance(factory_, type) and issubclass(factory_, BaseFactory):
            self.factory = factory_
            return

        if callable(factory_):
            self.callable = factory_
            return

        if not (isinstance(factory_, str) and "." in factory_):
            msg = (
                "The factory must be one of: "
                "1) a string with the format 'module.path.FactoryClass' "
                "2) a Factory class "
                "3) a callable that returns a Factory class"
            )
            raise ValueError(msg)

        self.callable = lambda: import_object(*factory_.rsplit(".", 1))

    def get(self):
        if self.factory is None:
            self.factory = self.callable()
        return self.factory


class PostFactory(PostGeneration, Generic[TModel]):
    def __init__(self, factory: FactoryType) -> None:
        super().__init__(function=self.generate)
        self.field_name: str = ""
        self.factory_wrapper = CustomFactoryWrapper(factory)

    def __set_name__(self, owner: Any, name: str) -> None:
        self.field_name = name

    def get_factory(self) -> BaseFactory:
        return self.factory_wrapper.get()

    def generate(self, instance: Model, create: bool, models: Optional[Iterable[TModel]], **kwargs: Any) -> None:
        raise NotImplementedError

    def manager(self, instance: Model) -> Any:
        return getattr(instance, self.field_name)


class ManyToManyFactory(PostFactory[TModel]):
    def generate(self, instance: Model, create: bool, models: Optional[Iterable[TModel]], **kwargs: Any) -> None:
        if not models and kwargs:
            factory = self.get_factory()
            model = factory.create(**kwargs) if create else factory.build(**kwargs)
            self.manager(instance).add(model)

        for model in models or []:
            self.manager(instance).add(model)


class OneToManyFactory(PostFactory[TModel]):
    def generate(self, instance: Model, create: bool, models: Optional[Iterable[TModel]], **kwargs: Any) -> None:
        if not models and kwargs:
            factory = self.get_factory()
            field_name = self.manager(instance).field.name
            kwargs.setdefault(field_name, instance)
            factory.create(**kwargs) if create else factory.build(**kwargs)


class ReverseSubFactory(PostFactory[TModel]):
    def generate(self, instance: Model, create: bool, models: Optional[Iterable[TModel]], **kwargs: Any) -> None:
        if not models and kwargs:
            factory = self.get_factory()
            field_name = instance._meta.get_field(self.field_name).remote_field.name
            kwargs.setdefault(field_name, instance)
            factory.create(**kwargs) if create else factory.build(**kwargs)


class NullableSubFactory(SubFactory, Generic[TModel]):
    def __init__(self, factory: FactoryType, null: bool = False, **kwargs) -> None:
        # Skip SubFactory.__init__ to replace its factory wrapper with ours
        self.null = null
        super(SubFactory, self).__init__(**kwargs)
        self.factory_wrapper = CustomFactoryWrapper(factory)

    def evaluate(self, instance: Resolver, step: BuildStep, extra: dict[str, Any]) -> Optional[TModel]:
        if not extra and self.null:
            return None
        return super().evaluate(instance, step, extra)
