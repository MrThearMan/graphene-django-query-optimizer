from __future__ import annotations

__all__ = [
    "OptimizerError",
]


class OptimizerError(Exception):
    """Expected error during the optimization compilation process."""
