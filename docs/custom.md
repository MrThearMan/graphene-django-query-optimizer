# Custom fields

Custom fields can be added to GraphQL types.

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

If the custom type requires fields from it's related models to resolve,
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
