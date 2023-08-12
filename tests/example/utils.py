from contextlib import contextmanager
from dataclasses import dataclass
from typing import Generator

import sqlparse
from django.conf import settings
from django.db import connection


@dataclass
class QueryResult:
    queries: list[str]
    message: str


@contextmanager
def count_queries() -> Generator[QueryResult, None, None]:
    orig_debug = settings.DEBUG
    settings.DEBUG = True

    results = QueryResult(queries=[], message="")
    old_queries = connection.queries_log.copy()
    connection.queries_log.clear()

    try:
        yield results
    finally:
        results.queries = [
            sqlparse.format(query["sql"], reindent=True)
            for query in connection.queries
            if "sql" in query
            and not query["sql"].startswith("SAVEPOINT")
            and not query["sql"].startswith("RELEASE SAVEPOINT")
        ]

        results.message = "-" * 75
        results.message += f"\n>>> Queries ({len(results.queries)}):\n"
        for index, query in enumerate(results.queries):
            results.message += f"{index + 1}) ".ljust(75, "-") + f"\n{query}\n"
        results.message += "-" * 75

        connection.queries_log.extendleft(reversed(old_queries))
        settings.DEBUG = orig_debug
