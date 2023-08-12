import logging
from contextlib import contextmanager
from dataclasses import dataclass
from typing import Any, Generator

import sqlparse
from django.conf import settings
from django.db import connection

logger = logging.getLogger(__name__)


@dataclass
class QueryResult:
    queries: list[str]


@contextmanager
def count_queries(*, log: bool = False) -> Generator[QueryResult, Any, None]:
    orig_debug = settings.DEBUG
    try:
        settings.DEBUG = True
        connection.queries_log.clear()
        results = QueryResult(queries=[])

        yield results

        results.queries = [
            sqlparse.format(query["sql"], reindent=True)
            for query in connection.queries
            if "sql" in query
            and not query["sql"].startswith("SAVEPOINT")
            and not query["sql"].startswith("RELEASE SAVEPOINT")
        ]

        if log:
            msg = "-" * 75
            msg += f"\n>>> Queries ({len(results.queries)}):\n"
            for index, query in enumerate(results.queries):
                msg += f"{index + 1}) ".ljust(75, "-") + f"\n{query}\n"

            msg += "-" * 75
            logger.info(msg)

    finally:
        connection.queries_log.clear()
        settings.DEBUG = orig_debug
