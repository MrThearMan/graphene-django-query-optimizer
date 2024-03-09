from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .typing import Any, Callable, TypeVar

    TCallable = TypeVar("TCallable", bound=Callable)


__all__ = [
    "required_annotations",
    "required_fields",
    "required_relations",
]


def required_fields(*args: str) -> Callable[[TCallable], TCallable]:
    """
    Add hints to a resolver to require given fields
    in relation to its DjangoObjectType model.

    Note: fields cannot be "relation fields" (e.g., foreign keys or many-to-many fields).
    Use `required_relations` to add those.

    :param args: Fields that the decorated resolver needs.
                 Related entity fields can also be used with
                 the field lookup syntax (e.g., 'related__field')
    """

    def decorator(resolver: TCallable) -> TCallable:
        resolver.fields = args  # type: ignore[attr-defined]
        return resolver

    return decorator


def required_relations(*args: str) -> Callable[[TCallable], TCallable]:
    """
    Add hints to a resolver to require given "relation fields"
    (e.g., foreign keys or many-to-many fields) in relation to its DjangoObjectType model.

    :param args: Relations that the decorated resolver needs.
    """

    def decorator(resolver: TCallable) -> TCallable:
        resolver.relations = args  # type: ignore[attr-defined]
        return resolver

    return decorator


def required_annotations(**kwargs: Any) -> Callable[[TCallable], TCallable]:
    """
    Add hints to a resolver function indicating that the given annotations
    should be applied to the ObjectType queryset _after_ filters are applied.
    See. https://docs.djangoproject.com/en/dev/topics/db/aggregation/#order-of-annotate-and-filter-clauses

    :param kwargs: Annotations that the decorated resolver needs.
                   Values should be Expression or F-object instances,
                   or any other value that works with queryset.annotate().
    """

    def decorator(resolver: TCallable) -> TCallable:
        resolver.annotations = kwargs  # type: ignore[attr-defined]
        return resolver

    return decorator
