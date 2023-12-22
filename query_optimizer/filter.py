from __future__ import annotations

import graphene_django.filter

from .fields import ConnectionFieldCachingMixin

__all__ = [
    "DjangoFilterConnectionField",
]


class DjangoFilterConnectionField(
    ConnectionFieldCachingMixin,
    graphene_django.filter.DjangoFilterConnectionField,
):
    pass
