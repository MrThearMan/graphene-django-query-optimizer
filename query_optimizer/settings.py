from __future__ import annotations

from typing import TYPE_CHECKING

from django.test.signals import setting_changed  # type: ignore[attr-defined]
from settings_holder import SettingsHolder, reload_settings

from .typing import NamedTuple

if TYPE_CHECKING:
    from .typing import Any, Union


__all__ = [
    "optimizer_settings",
]


SETTING_NAME: str = "GRAPHQL_QUERY_OPTIMIZER"


class DefaultSettings(NamedTuple):
    OPTIMIZER_MARK: str = "_optimized"
    """Key used mark if a queryset has been optimized by the query optimizer."""

    PREFETCH_COUNT_KEY: str = "_optimizer_count"
    """Name used for annotating the prefetched queryset total count."""

    PREFETCH_SLICE_START: str = "_optimizer_slice_start"
    """Name used for aliasing the prefetched queryset slice start."""

    PREFETCH_SLICE_STOP: str = "_optimizer_slice_stop"
    """Name used for aliasing the prefetched queryset slice end."""

    PREFETCH_PARTITION_INDEX: str = "_optimizer_partition_index"
    """Name used for aliasing the prefetched queryset partition index."""

    DISABLE_ONLY_FIELDS_OPTIMIZATION: bool = False
    """Disable optimizing fetched fields with `queryset.only()`."""

    MAX_COMPLEXITY: int = 10
    """Default max number of 'select_related' and 'prefetch related' joins optimizer is allowed to optimize."""

    SKIP_OPTIMIZATION_ON_ERROR: bool = False
    """If there is an unexpected error, should the optimizer skip optimization (True) or throw an error (False)?"""

    DEFAULT_FILTERSET_CLASS: str = ""
    """The default filterset class to use."""

    TOTAL_COUNT_FIELD: str = "totalCount"
    """The field name to use for fetching total count in connection fields."""

    ALLOW_CONNECTION_AS_DEFAULT_NESTED_TO_MANY_FIELD: bool = False
    """
    Should DjangoConnectionField be allowed to be generated for nested to-many fields
    if the ObjectType has a connection? If False (default), always use DjangoListFields.
    Doesn't prevent defining a DjangoConnectionField on the ObjectType manually.
    """


DEFAULTS: dict[str, Any] = DefaultSettings()._asdict()
IMPORT_STRINGS: set[Union[bytes, str]] = set()
REMOVED_SETTINGS: set[str] = {
    "PK_CACHE_KEY",
    "DONT_OPTIMIZE_ON_ERROR",
    "QUERY_CACHE_KEY",
}

optimizer_settings = SettingsHolder(
    setting_name=SETTING_NAME,
    defaults=DEFAULTS,
    import_strings=IMPORT_STRINGS,
    removed_settings=REMOVED_SETTINGS,
)

reload_my_settings = reload_settings(SETTING_NAME, optimizer_settings)
setting_changed.connect(reload_my_settings)
