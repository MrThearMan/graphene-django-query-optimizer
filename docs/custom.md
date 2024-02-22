# Custom fields

GraphQL types can have non-model fields using custom resolvers.

```python
import graphene
from query_optimizer import DjangoObjectType
from query_optimizer.typing import GQLInfo
from tests.example.models import HousingCompany

class HousingCompanyType(DjangoObjectType):
    class Meta:
        model = HousingCompany

    greeting = graphene.String()

    def resolve_greeting(model: HousingCompany, info: GQLInfo) -> str:
        return f"Hello World!"
```

If the custom type requires fields from its related models to resolve,
you can use the included `required_fields` decorator to make sure they
are fetched from the database.

```python
import graphene
from query_optimizer import DjangoObjectType, required_fields  # new import
from query_optimizer.typing import GQLInfo
from tests.example.models import HousingCompany

class HousingCompanyType(DjangoObjectType):
    class Meta:
        model = HousingCompany

    greeting = graphene.String()
    manager = graphene.String()
    primary_real_estate = graphene.String()

    @required_fields("name")  # fetched
    def resolve_greeting(model: HousingCompany, info: GQLInfo) -> str:
        return f"Hello {model.name}!"

    @required_fields("property_manager__name")  # selected
    def resolve_manager(model: HousingCompany, info: GQLInfo) -> str:
        return model.property_manager.name

    @required_fields("real_estates__name")  # prefetched
    def resolve_primary_real_estate(model: HousingCompany, info: GQLInfo) -> str:
        return model.real_estates.first().name
```

If the field you want to expose is purely computational, you can use `@required_annotations`
instead to add an annotation to the queryset when the field is requested.

```python
import graphene
from django.db.models import Value
from django.db.models.functions import Concat
from query_optimizer import DjangoObjectType, required_annotations  # new import
from query_optimizer.typing import GQLInfo
from tests.example.models import HousingCompany

class HousingCompanyType(DjangoObjectType):
    class Meta:
        model = HousingCompany

    address = graphene.String()

    @required_annotations(address=Concat("street_address", Value(", "), "postal_code__code", "city"))
    def resolve_address(model: HousingCompany, info: GQLInfo) -> str:
        return f"Hello {model.address}!"
```
