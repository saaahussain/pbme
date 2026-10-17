from __future__ import annotations

from typing import Any


class ResponseFilter:
    """Defense-in-depth filter for structured tool responses."""

    def filter(self, data: Any, allowed_fields: list[str]) -> Any:
        allowed = set(allowed_fields)

        if isinstance(data, list):
            return [self.filter(item, allowed_fields) for item in data]

        if isinstance(data, dict):
            return {
                key: value
                for key, value in data.items()
                if key in allowed
            }

        # Scalars contain no independently filterable field. The tool metadata
        # must explicitly describe scalar release in a future adapter.
        return data
