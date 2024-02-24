from query_optimizer.typing import NamedTuple, TypedDict, TypeVar

__all__ = [
    "parametrize_helper",
]


TNamedTuple = TypeVar("TNamedTuple", bound=NamedTuple)


class ParametrizeArgs(TypedDict):
    argnames: list[str]
    argvalues: list[TNamedTuple]
    ids: list[str]


def parametrize_helper(__tests: dict[str, TNamedTuple], /) -> ParametrizeArgs:
    """Construct parametrize input while setting test IDs."""
    assert __tests, "I need some tests, please!"  # noqa: S101
    values = list(__tests.values())
    try:
        return ParametrizeArgs(
            argnames=list(values[0].__class__.__annotations__),
            argvalues=values,
            ids=list(__tests),
        )
    except AttributeError as error:  # pragma: no cover
        msg = "Improper configuration. Did you use a NamedTuple for TNamedTuple?"
        raise RuntimeError(msg) from error
