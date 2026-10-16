"""
Test setup for tests ported from Undine's optimizer test suite.

The `graphql` fixture mirrors the API of Undine's test client (`pytest_undine.client.GraphQLClient`),
so that the ported tests can stay close to the originals. Instead of setting `undine_settings.SCHEMA`,
tests set `graphql.schema` to a schema created for that test.
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING, Any

import pytest
from django.contrib.auth.models import AnonymousUser
from django.test.client import RequestFactory
from graphene_django import registry as graphene_django_registry
from graphene_django.registry import Registry

from example_project.app.utils import capture_database_queries
from tests.undine_port.factories._base import UndineFaker

if TYPE_CHECKING:
    from collections.abc import Generator

    import graphene

    from example_project.app.utils import QueryData


class GraphQLResponse:
    def __init__(self, result: dict[str, Any], queries: QueryData | None) -> None:
        self.json = result
        self._queries = queries

    def __str__(self) -> str:
        return json.dumps(self.json, indent=2, sort_keys=True, default=str)

    def __getitem__(self, item: str) -> Any:
        return self.json[item]

    def __contains__(self, item: str) -> bool:
        return item in self.json

    def _require_queries(self) -> QueryData:
        if self._queries is None:
            pytest.fail("Database queries have not been captured. Use `count_queries=True`.")
        return self._queries

    @property
    def queries(self) -> list[str]:
        return self._require_queries().queries

    @property
    def query_count(self) -> int:
        return self._require_queries().count

    @property
    def query_log(self) -> str:
        return self._require_queries().log

    @property
    def data(self) -> dict[str, Any] | None:
        return self.json.get("data")

    @property
    def results(self) -> Any:
        data = self.data or {}
        try:
            return next(iter(data.values()))
        except StopIteration:
            return pytest.fail(f"No query object found in response content\nContent: {self.json}")

    @property
    def edges(self) -> list[dict[str, Any]]:
        results = self.results
        try:
            return results["edges"]
        except (KeyError, TypeError):
            return pytest.fail(f"Edges not found in response content\nContent: {self.json}")

    def node(self, index: int) -> dict[str, Any]:
        try:
            return self.edges[index]["node"]
        except (IndexError, TypeError):
            return pytest.fail(f"Node {index!r} not found in response content\nContent: {self.json}")

    @property
    def has_errors(self) -> bool:
        return self.json.get("errors") is not None

    @property
    def errors(self) -> list[dict[str, Any]]:
        try:
            return self.json["errors"]
        except KeyError:
            return pytest.fail(f"Errors not found in response content\nContent: {self.json}")

    def error_message(self, selector: int | str) -> str:
        if isinstance(selector, int):
            return self.errors[selector]["message"]
        return next(error["message"] for error in self.errors if error["path"][-1] == selector)

    def assert_query_count(self, count: int) -> None:
        if self.query_count != count:
            pytest.fail(f"Expected {count} queries, got {self.query_count}.\n{self.query_log}")


class GraphQLClient:
    def __init__(self) -> None:
        self.schema: graphene.Schema | None = None

    def __call__(
        self,
        query: str,
        *,
        variables: dict[str, Any] | None = None,
        operation_name: str | None = None,
        count_queries: bool = False,
    ) -> GraphQLResponse:
        if self.schema is None:
            pytest.fail("Set `graphql.schema` before making a query.")

        request = RequestFactory().post("/graphql/")
        request.user = AnonymousUser()

        if count_queries:
            with capture_database_queries() as queries:
                result = self.schema.execute(
                    query,
                    variable_values=variables,
                    operation_name=operation_name,
                    context_value=request,
                )
        else:
            queries = None
            result = self.schema.execute(
                query,
                variable_values=variables,
                operation_name=operation_name,
                context_value=request,
            )

        return GraphQLResponse(result=result.formatted, queries=queries)


@pytest.fixture
def graphql() -> GraphQLClient:
    return GraphQLClient()


@pytest.fixture(autouse=True)
def _fresh_global_registry() -> Generator[None, None, None]:
    """
    Use a fresh graphene-django global registry for each test, so that the types created
    for a test don't collide with the main schema or other tests. The optimizer looks up
    object types from the global registry, so a registry given in `Meta` would not work.
    """
    original = graphene_django_registry.registry
    graphene_django_registry.registry = Registry()
    try:
        yield
    finally:
        graphene_django_registry.registry = original


@pytest.fixture(autouse=True)
def _reset_faker_uniqueness() -> None:
    UndineFaker.clear_unique()
