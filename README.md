# Graphene Django Query Optimizer

[![Coverage Status][coverage-badge]][coverage]
[![GitHub Workflow Status][status-badge]][status]
[![PyPI][pypi-badge]][pypi]
[![GitHub][licence-badge]][licence]
[![GitHub Last Commit][repo-badge]][repo]
[![GitHub Issues][issues-badge]][issues]
[![Downloads][downloads-badge]][pypi]
[![Python Version][version-badge]][pypi]

```shell
pip install graphene-django-query-optimizer
```

---

**Documentation**: [https://mrthearman.github.io/graphene-django-query-optimizer/](https://mrthearman.github.io/graphene-django-query-optimizer/)

**Source Code**: [https://github.com/MrThearMan/graphene-django-query-optimizer/](https://github.com/MrThearMan/graphene-django-query-optimizer/)

**Contributing**: [https://github.com/MrThearMan/graphene-django-query-optimizer/blob/main/CONTRIBUTING.md](https://github.com/MrThearMan/graphene-django-query-optimizer/blob/main/CONTRIBUTING.md)

---

Solve the GraphQL [N+1 problem] in [graphene-django] applications
just by changing a few imports, automatically adding the appropriate
[`only`](https://docs.djangoproject.com/en/dev/ref/models/querysets/#only),
[`select_related`](https://docs.djangoproject.com/en/dev/ref/models/querysets/#select-related),
and [`prefetch_related`](https://docs.djangoproject.com/en/dev/ref/models/querysets/#prefetch-related)
method calls to your QuerySets to fetch _only_ what you need.

```python
import graphene
from tests.example.models import Example

from query_optimizer import DjangoObjectType, DjangoListField

class ExampleType(DjangoObjectType):
    class Meta:
        model = Example

class Query(graphene.ObjectType):
    all_examples = DjangoListField(ExampleType)

schema = graphene.Schema(query=Query)
```

[coverage-badge]: https://coveralls.io/repos/github/MrThearMan/graphene-django-query-optimizer/badge.svg?branch=main
[coverage]: https://coveralls.io/github/MrThearMan/graphene-django-query-optimizer?branch=main
[downloads-badge]: https://img.shields.io/pypi/dm/graphene-django-query-optimizer
[graphene-django]: https://github.com/graphql-python/graphene-django
[issues-badge]: https://img.shields.io/github/issues-raw/MrThearMan/graphene-django-query-optimizer
[issues]: https://github.com/MrThearMan/graphene-django-query-optimizer/issues
[licence-badge]: https://img.shields.io/github/license/MrThearMan/graphene-django-query-optimizer
[licence]: https://github.com/MrThearMan/graphene-django-query-optimizer/blob/main/LICENSE
[N+1 problem]: https://stackoverflow.com/a/97253
[pypi-badge]: https://img.shields.io/pypi/v/graphene-django-query-optimizer
[pypi]: https://pypi.org/project/graphene-django-query-optimizer
[repo-badge]: https://img.shields.io/github/last-commit/MrThearMan/graphene-django-query-optimizer
[repo]: https://github.com/MrThearMan/graphene-django-query-optimizer/commits/main
[status-badge]: https://img.shields.io/github/actions/workflow/status/MrThearMan/graphene-django-query-optimizer/test.yml?branch=main
[status]: https://github.com/MrThearMan/graphene-django-query-optimizer/actions/workflows/test.yml
[version-badge]: https://img.shields.io/pypi/pyversions/graphene-django-query-optimizer
