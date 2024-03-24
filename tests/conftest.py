import json

import pytest
from django.test.client import Client
from graphene_django.utils.testing import graphql_query

from query_optimizer.typing import Any, Callable, NamedTuple, Optional, Union
from tests.example.types import BuildingNode
from tests.example.utils import QueryData, capture_database_queries


class GraphQLResponse(NamedTuple):
    content: Union[dict[str, Any], list[dict[str, Any]], None]
    errors: Optional[list[dict[str, Any]]]
    queries: QueryData

    @property
    def no_errors(self):
        return self.errors is None


@pytest.fixture()
def graphql_client(client: Client) -> Callable[..., GraphQLResponse]:
    def func(*args, **kwargs) -> GraphQLResponse:
        with capture_database_queries() as queries:
            response = graphql_query(*args, **kwargs, client=client)

        full_content = json.loads(response.content)
        errors = full_content.get("errors")
        content = next(iter(full_content.get("data", {}).values()), None)

        return GraphQLResponse(
            content=content,
            errors=errors,
            queries=queries,
        )

    return func


@pytest.fixture()
def _set_building_node_apartments_max_limit() -> int:
    limit = BuildingNode.apartments.max_limit
    try:
        BuildingNode.apartments.max_limit = 1
        yield
    finally:
        BuildingNode.apartments.max_limit = limit


@pytest.fixture()
def _remove_apartment_node_apartments_max_limit() -> int:
    limit = BuildingNode.apartments.max_limit
    try:
        BuildingNode.apartments.max_limit = None
        yield
    finally:
        BuildingNode.apartments.max_limit = limit
