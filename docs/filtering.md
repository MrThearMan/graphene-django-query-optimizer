# Filtering

For adding additional filtering, optional dependency [django-filter][filters]
is required.

```python
import graphene
from graphene import relay
from example_project.app.models import Apartment

from query_optimizer import DjangoObjectType, DjangoConnectionField

class ApartmentNode(DjangoObjectType):
    class Meta:
        model = Apartment
        filter_fields = {
            "street_address": ["exact"],
            "building__name": ["exact"],
        }
        interfaces = (relay.Node,)


class Query(graphene.ObjectType):
    paged_apartments = DjangoConnectionField(ApartmentNode)


schema = graphene.Schema(query=Query)
```

We can also implement a custom Filterset class to have more control over the filtering.

```python
from example_project.app.models import Apartment

from django_filters import FilterSet

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
