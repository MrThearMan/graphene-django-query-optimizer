# Custom fields

GraphQL types can have non-model fields using custom resolvers.

```python
import graphene
from tests.example.models import HousingCompany

from query_optimizer import DjangoObjectType

class HousingCompanyType(DjangoObjectType):
    class Meta:
        model = HousingCompany

    greeting = graphene.String()

    def resolve_greeting(root: HousingCompany, info) -> str:
        return f"Hello World!"
```

If the custom type requires fields from its related models to resolve,
you have a few options.

## AnnotatedField

This field can be used to add annotations to the queryset when the field is requested.

```python
import graphene
from django.db.models import F, Value
from tests.example.models import HousingCompany

from query_optimizer import DjangoObjectType, AnnotatedField  # new import

class HousingCompanyType(DjangoObjectType):
    class Meta:
        model = HousingCompany

    greeting = AnnotatedField(graphene.String, expression=Value("Hello ") + F("name"))
```

Note that only a single annotation can be added, however, you can use the `aliases`
parameter to help with more complex annotations.

```python
import graphene
from django.db.models import F, Value
from tests.example.models import HousingCompany

from query_optimizer import DjangoObjectType, AnnotatedField

class HousingCompanyType(DjangoObjectType):
    class Meta:
        model = HousingCompany

    greeting = AnnotatedField(
        graphene.String,
        expression=F("hello") + F("name"),
        aliases={"hello": Value("Hello ")},  # very complex!
    )
```

## MultiField

This field can be used to add multiple fields to the queryset when the field is requested.

```python
import graphene
from tests.example.models import HousingCompany

from query_optimizer import DjangoObjectType, MultiField  # new import

class HousingCompanyType(DjangoObjectType):
    class Meta:
        model = HousingCompany

    greeting = MultiField(graphene.String, fields=["pk", "name"])

    def resolve_greeting(root: HousingCompany, info) -> str:
        return f"Hello {root.name} ({root.pk})!"
```

Note that this can only be used for fields on the same model.

## ManuallyOptimizedField

This is the most powerful custom field type, which allows defining a custom method to
manually optimize the queryset when the field is requested. This allows for optimization
strategies that are not possible with the other fields.

> **Note:** You shouldn't default to using this field, as it can break the optimization
> if you are not careful in considering other optimization already in the optimizer.

```python
import graphene
from django.db.models import QuerySet
from tests.example.models import HousingCompany

from query_optimizer import DjangoObjectType, ManuallyOptimizedField  # new import
from query_optimizer.optimizer import QueryOptimizer  # for type hinting

class HousingCompanyType(DjangoObjectType):
    class Meta:
        model = HousingCompany

    extra = ManuallyOptimizedField(graphene.String)

    @staticmethod
    def optimize_extra(queryset: QuerySet, optimizer: QueryOptimizer, **kwargs) -> QuerySet:
        # Do any optimizations here, returning the queryset.
        return queryset

    def resolve_extra(root: HousingCompany, info) -> str:
        # Still needs a resolver.
        return ...
```

Note that this can only be used for fields on the same model.

## The `field_name` argument

`RelatedField`, `DjangoListField`, `DjangoConnectionField` have a `field_name`
argument that can be used to specify the field name in the queryset if it's
different from the field name in the model.

```python
from tests.example.models import HousingCompany

from query_optimizer import DjangoObjectType, DjangoListField  # new import

class HousingCompanyType(DjangoObjectType):
    class Meta:
        model = HousingCompany

    developers_alt = DjangoListField("...", field_name="developers")
```

This marks the field as being for the same relation as the `field_name` is on the model,
and it will resolve the field as if it was that relation. This is achieved by using the
`Prefetch("developers", qs, to_attr="developers_alt")` feature from Django.
