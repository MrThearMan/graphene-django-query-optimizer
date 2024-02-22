# Filtering

For adding additional filtering, we need to use `DjangoFilterConnectionField`
instead of `DjangoConnectionField`. An optional dependency [django-filter][filters]
is required this.

```python
import graphene
from graphene import relay
from query_optimizer import DjangoObjectType
from query_optimizer.filter import DjangoFilterConnectionField  # new import
from tests.example.models import Apartment


class ApartmentNode(DjangoObjectType):
    class Meta:
        model = Apartment
        filter_fields = {
            "street_address": ["exact"],
            "building__name": ["exact"],
        }
        interfaces = (relay.Node,)


class Query(graphene.ObjectType):
    paged_apartments = DjangoFilterConnectionField(ApartmentNode)


schema = graphene.Schema(query=Query)
```

We can also implement a custom Filterset class to have more control over the filtering.

```python
from query_optimizer.filter import FilterSet  # new import
from tests.example.models import Apartment

class ApartmentFilterSet(FilterSet):
    # Custom filters can be added here

    class Meta:
        model = Apartment
        fields = [
            "completion_date",
            "street_address",
            "stair",
            "floor",
            "apartment_number",
        ]
```

These filters are for client side filtering. If you want to do server side filtering,
for example to automatically remove rows the user doesn't have access to, we can use
the `filter_queryset` method of the `DjangoObjectType` class.

```python
from django.db.models import QuerySet
from query_optimizer import DjangoObjectType
from query_optimizer.typing import GQLInfo

class ApartmentType(DjangoObjectType):
    @classmethod
    def filter_queryset(cls, queryset: QuerySet, info: GQLInfo) -> QuerySet:
        # Add your custom filtering here
        return queryset.filter(...)
```

The optimizer will find this method and use it automatically when this
object type is used in a query. No additional queries are performed when using
this method as opposed to overriding the `get_queryset` method itself.

[filters]: https://github.com/carltongibson/django-filter
