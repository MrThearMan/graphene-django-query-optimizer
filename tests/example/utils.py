from contextlib import contextmanager
from dataclasses import dataclass
from functools import partial

import sqlparse
from django import db

from query_optimizer.typing import Any, Callable, Generator


@dataclass
class QueryData:
    queries: list[str]

    @property
    def query_count(self) -> int:
        return len(self.queries)

    @property
    def log(self) -> str:
        message = "-" * 75
        message += f"\n>>> Queries ({len(self.queries)}):\n"
        for index, query in enumerate(self.queries):
            formatted_query = sqlparse.format(query, reindent=True)
            message += f"{index + 1}) ".ljust(75, "-") + f"\n{formatted_query}\n"
        message += "-" * 75
        return message


def _db_query_logger(
    execute: Callable[..., Any],
    sql: str,
    params: tuple[Any, ...],
    many: bool,  # noqa: FBT001
    context: dict[str, Any],
    # Added with functools.partial()
    query_cache: list[str],
) -> Any:
    """
    A database query logger for capturing executed database queries.
    Used to check that query optimizations work as expected.

    Can also be used as a place to put debugger breakpoint for solving issues.
    """
    # Don't include transaction creation, as we aren't interested in them.
    if not sql.startswith("SAVEPOINT") and not sql.startswith("RELEASE SAVEPOINT"):
        try:
            query_cache.append(sql % params)
        except TypeError:  # pragma: no cover
            query_cache.append(sql)
    return execute(sql, params, many, context)


@contextmanager
def capture_database_queries() -> Generator[QueryData, None, None]:
    """Capture results of what database queries were executed. `DEBUG` needs to be set to True."""
    results = QueryData(queries=[])
    query_logger = partial(_db_query_logger, query_cache=results.queries)

    with db.connection.execute_wrapper(query_logger):
        yield results
