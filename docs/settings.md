# Settings

Here are the available settings.

| Setting                                            | Type | Default                      | Description                                                                                                                                                                                                                                                     |
|----------------------------------------------------|------|------------------------------|-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| `ALLOW_CONNECTION_AS_DEFAULT_NESTED_TO_MANY_FIELD` | bool | False                        | Should `DjangoConnectionField` be allowed to be generated for nested to-many fields if the `ObjectType` has a connection? If `False` (default), always use `DjangoListField`s. Doesn't prevent defining a `DjangoConnectionField` on the `ObjectType` manually. |
| `DEFAULT_FILTERSET_CLASS`                          | str  | ""                           | The default filterset class to use.                                                                                                                                                                                                                             |
| `DISABLE_ONLY_FIELDS_OPTIMIZATION`                 | str  | False                        | Set to `True` to disable optimizing fetched fields with `queryset.only()`.                                                                                                                                                                                      |
| `MAX_COMPLEXITY`                                   | int  | 10                           | Default max number of `select_related` and `prefetch_related` joins optimizer is allowed to optimize.                                                                                                                                                           |
| `OPTIMIZER_MARK`                                   | str  | "_optimized"                 | Key used mark if a queryset has been optimized by the query optimizer.                                                                                                                                                                                          |
| `PREFETCH_COUNT_KEY`                               | str  | "_optimizer_count"           | Name used for annotating the prefetched queryset total count.                                                                                                                                                                                                   |
| `PREFETCH_PARTITION_INDEX`                         | str  | "_optimizer_partition_index" | Name used for aliasing the prefetched queryset partition index.                                                                                                                                                                                                 |
| `PREFETCH_SLICE_START`                             | str  | "_optimizer_slice_start"     | Name used for aliasing the prefetched queryset slice start.                                                                                                                                                                                                     |
| `PREFETCH_SLICE_STOP`                              | str  | "_optimizer_slice_stop"      | Name used for aliasing the prefetched queryset slice end.                                                                                                                                                                                                       |
| `SKIP_OPTIMIZATION_ON_ERROR`                       | bool | False                        | If there is an unexpected error, should the optimizer skip optimization (True) or throw an error (False)?                                                                                                                                                       |
| `TOTAL_COUNT_FIELD`                                | str  | "totalCount"                 | The field name to use for fetching total count in connection fields.                                                                                                                                                                                            |

Set them under the `GRAPHQL_QUERY_OPTIMIZER` key in your projects `settings.py` like this:

```python
GRAPHQL_QUERY_OPTIMIZER = {
    "MAX_COMPLEXITY": 10,
}
```
