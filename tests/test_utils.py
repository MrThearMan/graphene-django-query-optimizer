from typing import NamedTuple

import pytest

from query_optimizer.utils import calculate_queryset_slice
from tests.helpers import parametrize_helper


class PaginationInput(NamedTuple):
    first: int | None = None
    last: int | None = None
    after: int | None = None
    before: int | None = None
    size: int = 100


class Params(NamedTuple):
    pagination_input: PaginationInput
    start: int
    stop: int


@pytest.mark.parametrize(
    **parametrize_helper(
        {
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
    ),
)
def test_calculate_queryset_slice(pagination_input, start, stop):
    cut = calculate_queryset_slice(**pagination_input._asdict())
    assert cut.start == start
    assert cut.stop == stop
