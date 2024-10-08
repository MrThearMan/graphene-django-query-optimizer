# Quickstart

The database schema these examples will be using can be seen [here][schema].

Let's say we have defined a graphql schema like this:

```python
import graphene
from graphene_django import DjangoObjectType, DjangoListField
from example_project.app.models import Apartment

class ApartmentType(DjangoObjectType):
    class Meta:
        model = Apartment

class Query(graphene.ObjectType):
    # Imagine the rest of the types are also here,
    # and we omit it for brevity.
    all_apartments = DjangoListField(ApartmentType)

schema = graphene.Schema(query=Query)
```

Now, based on our database schema, we want to make a query like this:

```graphql
query {
  allApartments {
    streetAddress
    stair
    apartmentNumber
    sales {
      purchaseDate
      ownerships {
        percentage
        owner {
          name
        }
      }
    }
  }
}
```

As is, this query will result in:

- 1 query for all apartments
- 1 query or _**each**_ sale
- 1 query for _**each**_ ownership in _**each**_ sale
- 1 query for _**each**_ owner in _**each**_ ownership in _**each**_ sale

Let's say that we have:

- a modest 20 apartments
- each apartment has 3 sales
- each sale has 2 ownerships

In total, that's...

```
1 + (20 * 3) + (20 * 3 * 2) + (20 * 3 * 2 * 1) = 301 queries
```

It's important to notice, that the amount of queries is proportional to the
amount of records in our database, so the number of queries is only going to increase.
This is called an [N+1 problem].

We are also over-fetching all fields on each model, and thus not taking advantage of
GraphQLs schema at all.

This is the issue this library hopes to solve.

> Shoutout to [graphene-django-optimizer][prev], which inspired this library.
> The library seem to no longer work in modern versions of `graphene-django`.
> Hopefully this library can replace it, while offering a cleaner API.

We can optimize this query by simply using `DjangoObjectType` from `query_optimizer`
instead of `graphene_django`

```python
import graphene
from example_project.app.models import Apartment

from query_optimizer import DjangoListField, DjangoObjectType

class ApartmentType(DjangoObjectType):
    class Meta:
        model = Apartment

class Query(graphene.ObjectType):
    all_apartments = DjangoListField(ApartmentType)

schema = graphene.Schema(query=Query)
```

We could also use the `optimize` function to wrap a custom resolver queryset:

```python
import graphene
from query_optimizer import DjangoObjectType, optimize  # new import
from example_project.app.models import Apartment

class ApartmentType(DjangoObjectType):
    class Meta:
        model = Apartment

class Query(graphene.ObjectType):
    all_apartments = graphene.List(ApartmentType)

    def resolve_all_apartments(root, info):
        return optimize(Apartment.objects.all(), info)  # wrapped function

schema = graphene.Schema(query=Query)
```

That's it!

With the following configuration, the same query will result in
just _**3**_ database queries, regardless of the number of database records.

- 1 query for all apartments
- 1 query for all sales in all apartments
- 1 query for all ownerships with their owners for each sale in each apartment

Also, the optimization will only fetch the fields given in the GraphQL query,
as the query intended.

See [technical details] on how this works.


[schema]: https://github.com/MrThearMan/graphene-django-query-optimizer/blob/main/tests/example/models.py
[N+1 problem]: https://stackoverflow.com/a/97253
[prev]: https://github.com/tfoxy/graphene-django-optimizer
[only]: https://docs.djangoproject.com/en/dev/ref/models/querysets/#only
[technical details]: https://mrthearman.github.io/graphene-django-query-optimizer/technical/
