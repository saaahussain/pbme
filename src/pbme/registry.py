from __future__ import annotations

from .models import ToolSpec


class ToolRegistry:
    def __init__(self):
        self._tools: dict[str, ToolSpec] = {}

    def register(self, spec: ToolSpec) -> None:
        if spec.name in self._tools:
            raise ValueError(f"Tool already registered: {spec.name}")
        self._tools[spec.name] = spec

    def get(self, name: str) -> ToolSpec:
        try:
            return self._tools[name]
        except KeyError as exc:
            raise KeyError(f"Unknown tool: {name}") from exc

    def for_capability(self, capability: str) -> list[ToolSpec]:
        return [
            tool for tool in self._tools.values()
            if capability in tool.capabilities
        ]

    def all(self) -> list[ToolSpec]:
        return list(self._tools.values())
