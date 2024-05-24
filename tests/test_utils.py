import pytest
from django.db import models

from query_optimizer.settings import optimizer_settings
from query_optimizer.typing import NamedTuple, Optional
from query_optimizer.utils import calculate_queryset_slice, calculate_slice_for_queryset, swappable_by_subclassing
from tests.example.models import Example
from tests.factories.example import ExampleFactory
from tests.helpers import parametrize_helper


class PaginationInput(NamedTuple):
    first: Optional[int] = None
    last: Optional[int] = None
    after: Optional[int] = None
    before: Optional[int] = None
    size: int = 100


class Params(NamedTuple):
    pagination_input: PaginationInput
    start: int
    stop: int


TEST_CASES = {
    "default": Params(
        pagination_input=PaginationInput(),
        start=0,
        stop=100,
    ),
    "after": Params(
        pagination_input=PaginationInput(after=1),
        start=1,
        stop=100,
    ),
    "before": Params(
        pagination_input=PaginationInput(before=99),
        start=0,
        stop=99,
    ),
    "first": Params(
        pagination_input=PaginationInput(first=10),
        start=0,
        stop=10,
    ),
    "last": Params(
        pagination_input=PaginationInput(last=10),
        start=90,
        stop=100,
    ),
    "after_before": Params(
        pagination_input=PaginationInput(after=1, before=99),
        start=1,
        stop=99,
    ),
    "first_last": Params(
        pagination_input=PaginationInput(first=10, last=8),
        start=2,
        stop=10,
    ),
    "after_before_first_last": Params(
        pagination_input=PaginationInput(after=1, before=99, first=10, last=8),
        start=3,
        stop=11,
    ),
    "after_bigger_than_size": Params(
        pagination_input=PaginationInput(after=101),
        start=100,
        stop=100,
    ),
    "before_bigger_than_size": Params(
        pagination_input=PaginationInput(before=101),
        start=0,
        stop=100,
    ),
    "first_bigger_than_size": Params(
        pagination_input=PaginationInput(first=101),
        start=0,
        stop=100,
    ),
    "last_bigger_than_size": Params(
        pagination_input=PaginationInput(last=101),
        start=0,
        stop=100,
    ),
    "after_is_size": Params(
        pagination_input=PaginationInput(after=100),
        start=100,
        stop=100,
    ),
    "before_is_size": Params(
        pagination_input=PaginationInput(before=100),
        start=0,
        stop=100,
    ),
    "first_is_size": Params(
        pagination_input=PaginationInput(first=100),
        start=0,
        stop=100,
    ),
    "last_is_size": Params(
        pagination_input=PaginationInput(last=100),
        start=0,
        stop=100,
    ),
    "first_bigger_than_after_before": Params(
        pagination_input=PaginationInput(after=10, before=20, first=20),
        start=10,
        stop=20,
    ),
    "last_bigger_than_after_before": Params(
        pagination_input=PaginationInput(after=10, before=20, last=20),
        start=10,
        stop=20,
    ),
}


@pytest.mark.parametrize(**parametrize_helper(TEST_CASES))
def test_calculate_queryset_slice(pagination_input: PaginationInput, start: int, stop: int) -> None:
    cut = calculate_queryset_slice(**pagination_input._asdict())
    assert cut.start == start
    assert cut.stop == stop


@pytest.mark.django_db()
@pytest.mark.parametrize(**parametrize_helper(TEST_CASES))
def test_calculate_slice_for_queryset(pagination_input: PaginationInput, start: int, stop: int) -> None:
    ExampleFactory.create()

    qs = Example.objects.all()
    qs = qs.annotate(**{optimizer_settings.PREFETCH_COUNT_KEY: models.Value(pagination_input.size)})

    qs = calculate_slice_for_queryset(qs, **pagination_input._asdict())

    values = (
        qs.annotate(
            start=models.F(optimizer_settings.PREFETCH_SLICE_START),
            stop=models.F(optimizer_settings.PREFETCH_SLICE_STOP),
        )
        .values("start", "stop")
        .first()
    )

    assert values == {"start": start, "stop": stop}


def test_swappable_by_subclassing():
    @swappable_by_subclassing
    class A:
        def __init__(self) -> None:
            self.one = 1

    a = A()
    assert type(a) is A
    assert a.one == 1

    class B(A):
        def __init__(self) -> None:
            super().__init__()
            self.two = 2

    b = A()
    assert type(b) is B
    assert b.one == 1
    assert b.two == 2

    class C(A):
        def __init__(self) -> None:
            super().__init__()
            self.three = 3

    c = A()
    assert type(c) is C
    assert c.one == 1
    assert not hasattr(c, "two")
    assert c.three == 3

    class D(B): ...

    d = A()
    assert type(d) is C  # Only direct subclasses are swapped.
