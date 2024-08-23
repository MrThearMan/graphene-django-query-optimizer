from __future__ import annotations

import traceback
from contextlib import contextmanager
from dataclasses import dataclass
from functools import partial
from pathlib import Path
from typing import TYPE_CHECKING

import sqlparse
from django import db
from django.db.backends import utils as _django_utils
from django.db.models.sql import compiler as _compiler
from django.db.models.sql import query as _query
from graphene_django import views as _views
from graphene_django.debug.sql import tracking as _tracking

from example_project.config import logging as _logging

if TYPE_CHECKING:
    from query_optimizer.typing import Any, Callable, Generator

# Paths for stack trace filtering.
BASE_PATH = str(Path(__file__).parent.parent.parent.resolve())
SKIP_PATHS = [
    str(Path(_query.__file__).resolve()),
    str(Path(_compiler.__file__).resolve()),
    str(Path(_tracking.__file__).resolve()),
    str(Path(_django_utils.__file__).resolve()),
    str(Path(_logging.__file__).resolve()),
]
STOP_PATH = str(Path(_views.__file__).resolve())


@dataclass
class QueryData:
    queries: list[str]
    stacks: list[str]

    def __str__(self) -> str:
        return f"QueryData with {len(self.queries)} queries."

    def __repr__(self) -> str:
        return "QueryData(queries=..., stacks=...)"

    @property
    def count(self) -> int:
        return len(self.queries)

    @property
    def log(self) -> str:
        message = "\n" + "-" * 75
        message += f"\n>>> Queries ({len(self.queries)}):\n\n"

        query: str
        summary: str
        for index, (query, summary) in enumerate(zip(self.queries, self.stacks)):
            message += f"{index + 1})"
            message += "\n\n"
            message += "--- Query ".ljust(75, "-")
            message += "\n\n"
            message += sqlparse.format(query, reindent=True)
            message += "\n\n"
            message += "--- Stack (abridged) ".ljust(75, "-")
            message += "\n\n"
            message += summary
            message += "\n"
            message += "-" * 75
            message += "\n\n"

        message += "-" * 75
        return message

    def __getitem__(self, item: int) -> str:
        return self.queries[item]


def db_query_logger(
    execute: Callable[..., Any],
    sql: str,
    params: tuple[Any, ...],
    many: bool,  # noqa: FBT001
    context: dict[str, Any],
    # Added with functools.partial()
    query_data: QueryData,
) -> Any:
    """
    A database query logger for capturing executed database queries.
    Used to check that query optimizations work as expected.

    Can also be used as a place to put debugger breakpoint for solving issues.
    """
    query_data.stacks.append(get_stack_info())

    # Don't include transaction creation, as we aren't interested in them.
    if not sql.startswith("SAVEPOINT") and not sql.startswith("RELEASE SAVEPOINT"):
        try:
            query_data.queries.append(sql % params)
        except TypeError:
            query_data.queries.append(sql)
    return execute(sql, params, many, context)


def get_stack_info() -> str:
    # Get the current stack for debugging purposes.
    # Don't include files from the skipped paths.
    stack: list[traceback.FrameSummary] = []
    skipped = 0  # How many frames have been skipped?
    to_skip = 2  # Skip the first two frames (this func and caller func)

    for frame in reversed(traceback.extract_stack()):
        if skipped < to_skip:
            skipped += 1
            continue

        is_skipped_path = any(frame.filename.startswith(path) for path in SKIP_PATHS)
        if is_skipped_path:
            continue

        is_stop_path = frame.filename.startswith(STOP_PATH)
        if is_stop_path:
            break

        stack.insert(0, frame)

        is_own_file = frame.filename.startswith(BASE_PATH)
        if is_own_file:
            break

    return "".join(traceback.StackSummary.from_list(stack).format())


@contextmanager
def capture_database_queries() -> Generator[QueryData, None, None]:
    """Capture results of what database queries were executed. `DEBUG` needs to be set to True."""
    query_data = QueryData(queries=[], stacks=[])
    query_logger = partial(db_query_logger, query_data=query_data)

    with db.connection.execute_wrapper(query_logger):
        yield query_data
