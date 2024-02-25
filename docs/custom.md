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
you can use the included `required_fields` decorator to make sure they
are fetched from the database.

```python
import graphene
from tests.example.models import HousingCompany

from query_optimizer import DjangoObjectType, required_fields  # new import

class HousingCompanyType(DjangoObjectType):
    class Meta:
        model = HousingCompany

    greeting = graphene.String()
    manager = graphene.String()
    primary_real_estate = graphene.String()

    @required_fields("name")  # fetched
    def resolve_greeting(root: HousingCompany, info) -> str:
        return f"Hello {root.name}!"

    @required_fields("property_manager__name")  # selected
    def resolve_manager(root: HousingCompany, info) -> str:
        return root.property_manager.name

    @required_fields("real_estates__name")  # prefetched
    def resolve_primary_real_estate(root: HousingCompany, info) -> str:
        return root.real_estates.first().name
```

If the field you want to expose is purely computational, you can use `@required_annotations`
instead to add an annotation to the queryset when the field is requested.

```python
import graphene
from django.db.models import Value
from django.db.models.functions import Concat
from tests.example.models import HousingCompany

from query_optimizer import DjangoObjectType, required_annotations

class HousingCompanyType(DjangoObjectType):
    class Meta:
        model = HousingCompany

    address = graphene.String()

    @required_annotations(address=Concat("street_address", Value(", "), "postal_code__code", "city"))
    def resolve_address(root: HousingCompany, info) -> str:
        return f"Hello {root.address}!"
```
