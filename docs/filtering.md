---
description: "How to filter optimized querysets with django-filter and object type filtering hooks."
---

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

`DjangoObjectType` is generic over the model, the user type and the queryset class.
Without subscription, the model is `Model`, the user is `User | AnonymousUser`,
and the queryset class is `QuerySet` of the model. Subscribe the class to type its methods
for a specific model, user and queryset class. `GQLInfo` is generic over
the user type in the same way:

```python
class ApartmentType(DjangoObjectType[Apartment, MyUser]):
    @classmethod
    def filter_queryset(cls, queryset: QuerySet[Apartment], info: GQLInfo[MyUser]) -> QuerySet[Apartment]:
        return queryset.filter(owner=info.context.user)
```

If the model's default manager uses a custom queryset class, give that class
as the third type. Then the methods of the custom queryset are typed in the hooks:

```python
class ApartmentQuerySet(QuerySet["Apartment"]):
    def with_rooms(self) -> Self:
        return self.filter(rooms__isnull=False)


class Apartment(models.Model):
    objects = ApartmentQuerySet.as_manager()


class ApartmentType(DjangoObjectType[Apartment, MyUser, ApartmentQuerySet]):
    @classmethod
    def filter_queryset(cls, queryset: ApartmentQuerySet, info: GQLInfo[MyUser]) -> ApartmentQuerySet:
        return queryset.with_rooms()
```

The type checker does not check that the hooks receive this queryset class.
Make sure that the model's default manager uses it.

[filters]: https://github.com/carltongibson/django-filter
