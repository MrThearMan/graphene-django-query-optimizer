# Depth Limiting

The `optimize()` function has builtin query depth limiting, which
will allow a maximum of 10 `select_related` and `prefetch_related` actions
per query by default. This should be a sensible limit that protects
your API from misuse, but if you need to change it, it can be done on
per resolver basis:

```python
import graphene
from query_optimizer import DjangoObjectType, optimize
from tests.example.models import Apartment

class ApartmentType(DjangoObjectType):
    class Meta:
        model = Apartment

class Query(graphene.ObjectType):
    all_apartments = graphene.List(ApartmentType)

    def resolve_all_apartments(root, info):
        return optimize(Apartment.objects.all(), info, max_complexity=4)  # changed

schema = graphene.Schema(query=Query)
```

...or per ObjectType basis for relay nodes and connections.

```python
import graphene
from graphene import relay
from query_optimizer import DjangoObjectType
from tests.example.models import Apartment

class ApartmentNode(DjangoObjectType):
    @classmethod
    def max_complexity(cls) -> int:
        return 4  # changed

    class Meta:
        model = Apartment
        interfaces = (relay.Node,)

class Query(graphene.ObjectType):
    apartment = relay.Node.Field(ApartmentNode)

schema = graphene.Schema(query=Query)
```

You can also set the `MAX_COMPLEXITY` setting in your project's settings.py
to set the value for all optimizers:

```python
GRAPHQL_QUERY_OPTIMIZER = {
    "MAX_COMPLEXITY": 15,
}
```
