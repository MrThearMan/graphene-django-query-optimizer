# Settings

Here are the available settings.

| Setting                            | Type | Default        | Description                                                                                               |
|------------------------------------|------|----------------|-----------------------------------------------------------------------------------------------------------|
| `QUERY_CACHE_KEY`                  | str  | "_query_cache" | Key to store fetched model instances under in the GraphQL schema extensions.                              |
| `OPTIMIZER_MARK`                   | str  | "_optimized"   | Key used mark if a queryset has been optimized by the query optimizer.                                    |
| `DISABLE_ONLY_FIELDS_OPTIMIZATION` | str  | False          | Set to `True` to disable optimizing fetched fields with `queryset.only()`.                                |
| `MAX_COMPLEXITY`                   | int  | 10             | Default max number of `select_related` and `prefetch_related` joins optimizer is allowed to optimize.     |
| `SKIP_OPTIMIZATION_ON_ERROR`       | bool | False          | If there is an unexpected error, should the optimizer skip optimization (True) or throw an error (False)? |
| `DEFAULT_FILTERSET_CLASS`          | str  | ""             | The default filterset class to use.                                                                       |

Set them under the `GRAPHQL_QUERY_OPTIMIZER` key in your projects `settings.py` like this:

```python
GRAPHQL_QUERY_OPTIMIZER = {
    "MAX_COMPLEXITY": 10,
}
```
