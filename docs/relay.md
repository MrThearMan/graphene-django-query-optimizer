# Relay

The optimization will also work with [Relay] Nodes.

## Nodes

Let's say we have the following node in out schema:

```python
import graphene
from graphene import relay
from graphene_django import DjangoObjectType
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
    apartment = relay.Node.Field(ApartmentNode)

schema = graphene.Schema(query=Query)
```

We can optimize this query by simply using `DjangoObjectType` from `query_optimizer`.

```python
import graphene
from graphene import relay
from query_optimizer import DjangoObjectType  # replaced import
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
    apartment = relay.Node.Field(ApartmentNode)

schema = graphene.Schema(query=Query)
```

That's it!

## Connections

Given the following connection in our schema:

```python
import graphene
from graphene import relay
from graphene_django import DjangoObjectType, DjangoConnectionField
from tests.example.models import Apartment

class ApartmentNode(DjangoObjectType):
    class Meta:
        model = Apartment
        interfaces = (relay.Node,)

class Query(graphene.ObjectType):
    paged_apartments = DjangoConnectionField(ApartmentNode)

schema = graphene.Schema(query=Query)
```

We can optimize this query by simply using `DjangoObjectType`
and `DjangoConnectionField` from `query_optimizer`, like this:

```python
import graphene
from graphene import relay
from query_optimizer import DjangoObjectType, DjangoConnectionField  # replaced import
from tests.example.models import Apartment

class ApartmentNode(DjangoObjectType):
    class Meta:
        model = Apartment
        interfaces = (relay.Node,)

class Query(graphene.ObjectType):
    paged_apartments = DjangoConnectionField(ApartmentNode)

schema = graphene.Schema(query=Query)
```

That's it!


[Relay]: https://relay.dev/docs/guides/graphql-server-specification/
