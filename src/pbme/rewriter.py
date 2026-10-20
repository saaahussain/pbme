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

        # PBME treats task selectors/identifiers as normal tool arguments, not
        # as data that must be hidden or replaced. The authority question is
        # where the argument value came from. Task-bound values come from the
        # trusted/signed task context (plan.parameters). Agent-provided values
        # are forwarded only when the tool explicitly marks the argument as
        # safe for agent control. This prevents an LLM from silently changing
        # task scope with an invented customer_id, department, year, etc.
        for name in selected_tool.agent_passthrough_arguments:
            if (
                name in selected_tool.accepted_arguments
                and name in proposed.arguments
            ):
                args[name] = proposed.arguments[name]

        # Signed task parameters are authoritative and override any proposed
        # value. IDs such as customer_id, invoice_id, or document_id are kept
        # unchanged when the trusted task actually requires them.
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
