from __future__ import annotations

from graphene_django.settings import graphene_settings
from graphql_relay import cursor_to_offset

from .typing import Optional, TypedDict

__all__ = [
    "validate_pagination_args",
]


class PaginationArgs(TypedDict):
    after: Optional[int]
    before: Optional[int]
    first: Optional[int]
    last: Optional[int]
    size: Optional[int]


def validate_pagination_args(  # noqa: C901, PLR0912
    first: Optional[int],
    last: Optional[int],
    offset: Optional[int],
    after: Optional[str],
    before: Optional[str],
    max_limit: Optional[int] = None,
) -> PaginationArgs:
    """
    Validate the pagination arguments and return a dictionary with the validated values.

    :param first: Number of records to return from the beginning.
    :param last: Number of records to return from the end.
    :param offset: Number of records to skip from the beginning.
    :param after: Cursor value for the last record in the previous page.
    :param before: Cursor value for the first record in the next page.
    :param max_limit: Maximum limit for the number of records that can be requested.
    :raises ValueError: Validation error.
    """
    after = cursor_to_offset(after) if after is not None else None
    before = cursor_to_offset(before) if before is not None else None

    if graphene_settings.RELAY_CONNECTION_ENFORCE_FIRST_OR_LAST and not (first or last):  # pragma: no cover
        msg = "You must provide a `first` or `last` for pagination."
        raise ValueError(msg)

    if first is not None:
        if not isinstance(first, int) or first <= 0:
            msg = "Argument 'first' must be a positive integer."
            raise ValueError(msg)

        if isinstance(max_limit, int) and first > max_limit:
            msg = f"Requesting first {first} records exceeds the limit of {max_limit}."
            raise ValueError(msg)

    if last is not None:
        if not isinstance(last, int) or last <= 0:
            msg = "Argument 'last' must be a positive integer."
            raise ValueError(msg)

        if isinstance(max_limit, int) and last > max_limit:
            msg = f"Requesting last {last} records exceeds the limit of {max_limit}."
            raise ValueError(msg)

    if isinstance(max_limit, int) and first is None and last is None:
        first = max_limit

    if offset is not None:
        if after is not None or before is not None:
            msg = "Can only use either `offset` or `before`/`after` for pagination."
            raise ValueError(msg)
        if not isinstance(offset, int) or offset < 0:
            msg = "Argument `offset` must be a positive integer."
            raise ValueError(msg)

        # Convert offset to after cursor value. Note that after cursor dictates
        # a value _after_ which results should be returned, so we need to subtract
        # 1 from the offset to get the correct cursor value.
        if offset > 0:  # ignore zero offset
            after = offset - 1

    if after is not None and (not isinstance(after, int) or after < 0):
        msg = "The node pointed with `after` does not exist."
        raise ValueError(msg)

    if before is not None and (not isinstance(before, int) or before < 0):
        msg = "The node pointed with `before` does not exist."
        raise ValueError(msg)

    if after is not None and before is not None and after >= before:
        msg = "The node pointed with `after` must be before the node pointed with `before`."
        raise ValueError(msg)

    # Since `after` is also exclusive, we need to add 1 to it, so that slicing works correctly.
    if after is not None:
        after += 1

    # Size is changed later with `queryset.count()`.
    size = max_limit if isinstance(max_limit, int) else None
    return PaginationArgs(after=after, before=before, first=first, last=last, size=size)
