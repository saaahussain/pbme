from __future__ import annotations

import os
from typing import Any

from .broker import PBMEBroker, PBMEDenied
from .context import TaskContextSigner
from .hr_setup import build_hr_environment
from .models import ProposedToolCall
from .planner import DeterministicInformationPlanner


def build_broker() -> PBMEBroker:
    _, catalog, registry = build_hr_environment()
    secret = os.environ.get(
        "PBME_CONTEXT_SECRET",
        "pbme-demo-secret-change-me",
    )
    return PBMEBroker(
        signer=TaskContextSigner(secret),
        catalog=catalog,
        registry=registry,
        planner=DeterministicInformationPlanner(),
    )


def create_server():
    # Imported lazily so the core package/tests run without MCP installed.
    from mcp.server import MCPServer

    mcp = MCPServer("PBME Protected HR Tools")
    broker = build_broker()

    @mcp.tool()
    def get_employee_data(
        task_token: str,
        fields: list[str],
        year: int | None = None,
        department: str | None = None,
    ) -> dict[str, Any]:
        """Protected employee-data access.

        PBME may narrow this call or reroute it to a lower-exposure tool.
        """
        try:
            result = broker.execute(
                task_token=task_token,
                proposed_call=ProposedToolCall(
                    tool_name="get_employee_data",
                    arguments={
                        "fields": fields,
                        "year": year,
                        "department": department,
                    },
                ),
            )
        except PBMEDenied as exc:
            return {
                "decision": "deny",
                "error": str(exc),
                "data": [],
            }

        e = result.enforcement
        return {
            "decision": e.decision.value,
            "selected_tool": e.selected_tool,
            "released_fields": e.released_fields,
            "data": result.data,
        }

    @mcp.tool()
    def turnover_by_department(
        task_token: str,
        year: int | None = None,
    ) -> dict[str, Any]:
        """Protected aggregate turnover query."""
        try:
            result = broker.execute(
                task_token=task_token,
                proposed_call=ProposedToolCall(
                    tool_name="turnover_by_department",
                    arguments={"year": year},
                ),
            )
        except PBMEDenied as exc:
            return {
                "decision": "deny",
                "error": str(exc),
                "data": [],
            }
        e = result.enforcement
        return {
            "decision": e.decision.value,
            "selected_tool": e.selected_tool,
            "released_fields": e.released_fields,
            "data": result.data,
        }

    @mcp.tool()
    def average_salary_by_department(
        task_token: str,
        department: str | None = None,
    ) -> dict[str, Any]:
        """Protected aggregate salary query."""
        try:
            result = broker.execute(
                task_token=task_token,
                proposed_call=ProposedToolCall(
                    tool_name="average_salary_by_department",
                    arguments={"department": department},
                ),
            )
        except PBMEDenied as exc:
            return {
                "decision": "deny",
                "error": str(exc),
                "data": [],
            }
        e = result.enforcement
        return {
            "decision": e.decision.value,
            "selected_tool": e.selected_tool,
            "released_fields": e.released_fields,
            "data": result.data,
        }

    return mcp


def main():
    mcp = create_server()
    mcp.run(transport="streamable-http", port=8000)


if __name__ == "__main__":
    main()
