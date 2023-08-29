from django.test.signals import setting_changed  # type: ignore[attr-defined]
from settings_holder import SettingsHolder, reload_settings

from .typing import Any, NamedTuple, Union

__all__ = [
    "optimizer_settings",
]

SETTING_NAME: str = "GRAPHQL_QUERY_OPTIMIZER"


class DefaultSettings(NamedTuple):
    QUERY_CACHE_KEY: str = "_query_cache"
    PK_CACHE_KEY: str = "_query_optimizer_model_pk"
    MAX_COMPLEXITY: int = 10


DEFAULTS: dict[str, Any] = DefaultSettings()._asdict()
IMPORT_STRINGS: set[Union[bytes, str]] = set()
REMOVED_SETTINGS: set[str] = set()

optimizer_settings = SettingsHolder(
    setting_name=SETTING_NAME,
    defaults=DEFAULTS,
    import_strings=IMPORT_STRINGS,
    removed_settings=REMOVED_SETTINGS,
)

reload_my_settings = reload_settings(SETTING_NAME, optimizer_settings)
setting_changed.connect(reload_my_settings)
