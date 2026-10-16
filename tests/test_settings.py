from __future__ import annotations

import pytest
from django.core.exceptions import ImproperlyConfigured

from query_optimizer.settings import optimizer_settings


def test_settings__removed_setting():
    with pytest.raises(ImproperlyConfigured, match=r"Setting 'GRAPHQL_QUERY_OPTIMIZER.PK_CACHE_KEY' has been removed."):
        _ = optimizer_settings.PK_CACHE_KEY
