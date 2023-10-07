# Fragments

## Fragment spreads

Example query:

```graphql
query {
  allApartments {
    ...Shares
  }
}

fragment Shares on ApartmentType {
  sharesStart
  sharesEnd
}
```

Fragments spreads like these are optimized without any additional setup.

## Inline fragments

Example query:

```graphql
query {
  allPeople {
    ... on DeveloperType {
      name
      housingCompanies {
        name
      }
      __typename
    }
    ... on PropertyManagerType {
      name
      housingCompanies {
        name
      }
      __typename
    }
    ... on OwnerType {
      name
      ownerships {
        percentage
      }
      __typename
    }
  }
}
```

Inline fragments like these can also be optimized.
Here is how you would construct a resolver like this:

```python
import itertools
import graphene
from query_optimizer import DjangoObjectType, optimize
from tests.example.models import Developer, PropertyManager, Owner

class DeveloperType(DjangoObjectType):
    class Meta:
        model = Developer

class PropertyManagerType(DjangoObjectType):
    class Meta:
        model = PropertyManager

class OwnerType(DjangoObjectType):
    class Meta:
        model = Owner

class People(graphene.Union):
    class Meta:
        types = (
            DeveloperType,
            PropertyManagerType,
            OwnerType,
        )

class Query(graphene.ObjectType):

    all_people = graphene.List(People)

    def resolve_all_people(parent, info):
        developers = optimize(Developer.objects.all(), info)
        property_managers = optimize(PropertyManager.objects.all(), info)
        owners = optimize(Owner.objects.all(), info)
        return itertools.chain(developers, property_managers, owners)

schema = graphene.Schema(query=Query)
```
