from contextlib import contextmanager
from dataclasses import dataclass
from typing import Generator

import sqlparse
from django import db


@dataclass
class QueryData:
    queries: list[str]

    @property
    def log(self) -> str:
        message = "-" * 75
        message += f"\n>>> Queries ({len(self.queries)}):\n"
        for index, query in enumerate(self.queries):
            message += f"{index + 1}) ".ljust(75, "-") + f"\n{query}\n"
        message += "-" * 75
        return message


@contextmanager
def capture_database_queries() -> Generator[QueryData, None, None]:
    """Capture results of what database queries were executed. `DEBUG` needs to be set to True."""
    results = QueryData(queries=[])
    db.connection.queries_log.clear()

    try:
        yield results
    finally:
        results.queries = [
            sqlparse.format(query["sql"], reindent=True)
            for query in db.connection.queries
            if "sql" in query
            and not query["sql"].startswith("SAVEPOINT")
            and not query["sql"].startswith("RELEASE SAVEPOINT")
        ]
