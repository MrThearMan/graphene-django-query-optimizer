from typing import Any, TypeAlias, TypeVar

import graphql
from django.core.handlers.wsgi import WSGIRequest
from django.db import models

__all__ = [
    "GQLInfo",
    "TModel",
]


class GQLInfo(graphql.GraphQLResolveInfo):
    context: WSGIRequest


TModel = TypeVar("TModel", bound=models.Model)
TableName: TypeAlias = str
StoreStr: TypeAlias = str
PK: TypeAlias = Any
QueryCache: TypeAlias = dict[TableName, dict[StoreStr, dict[PK, TModel]]]
