from __future__ import annotations

from typing import Any

from .models import NecessityPlan, ProposedToolCall, ToolSpec


class RequestRewriter:
    """Constructs the minimum executable call for a selected tool."""

    def build(
        self,
        *,
        selected_tool: ToolSpec,
        proposed: ProposedToolCall,
        plan: NecessityPlan,
    ) -> dict[str, Any]:
        args: dict[str, Any] = {}

        # Carry only arguments the selected tool understands.
        # Task-derived parameters override agent-provided values for authority-
        # relevant parameters such as year.
        for name in selected_tool.accepted_arguments:
            if name in proposed.arguments:
                args[name] = proposed.arguments[name]

        for name, value in plan.parameters.items():
            if name in selected_tool.accepted_arguments:
                args[name] = value

        if selected_tool.supports_projection:
            if not selected_tool.field_argument:
                raise ValueError(
                    f"Projection tool {selected_tool.name} has no field argument"
                )
            args[selected_tool.field_argument] = list(plan.required_fields)

        # Remove unknown arguments instead of forwarding them.
        return {
            k: v for k, v in args.items()
            if k in selected_tool.accepted_arguments
        }
