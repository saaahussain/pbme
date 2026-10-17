from __future__ import annotations

import json
from dataclasses import asdict

from .broker import PBMEBroker
from .context import TaskContextSigner
from .hr_setup import build_hr_environment
from .models import ProposedToolCall
from .planner import DeterministicInformationPlanner


DEMO_SECRET = "pbme-demo-secret-change-me"


def main():
    _, catalog, registry = build_hr_environment()
    signer = TaskContextSigner(DEMO_SECRET)
    broker = PBMEBroker(
        signer=signer,
        catalog=catalog,
        registry=registry,
        planner=DeterministicInformationPlanner(),
    )

    token = signer.issue(
        task_id="task-001",
        user_goal="Which department had the highest turnover in 2026?",
        approved_purpose="workforce_analytics",
        actor_id="hr-analyst-17",
    )

    proposed = ProposedToolCall(
        tool_name="get_employee_data",
        arguments={
            "fields": [
                "employee_id",
                "name",
                "ssn",
                "salary",
                "department",
                "termination_date",
                "email",
            ],
            "year": 2026,
        },
    )

    result = broker.execute(
        task_token=token,
        proposed_call=proposed,
    )

    print(json.dumps({
        "data": result.data,
        "decision": result.enforcement.decision.value,
        "selected_tool": result.enforcement.selected_tool,
        "executed_arguments": result.enforcement.executed_arguments,
        "released_fields": result.enforcement.released_fields,
        "removed_fields": result.enforcement.removed_fields,
        "exposure_before": result.enforcement.exposure_before,
        "exposure_after": result.enforcement.exposure_after,
        "rationale": result.enforcement.rationale,
    }, indent=2))


if __name__ == "__main__":
    main()
