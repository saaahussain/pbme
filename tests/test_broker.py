import pytest

from pbme.broker import PBMEBroker, PBMEDenied
from pbme.context import TaskContextSigner
from pbme.hr_setup import build_hr_environment
from pbme.models import ProposedToolCall
from pbme.planner import DeterministicInformationPlanner


SECRET = "1234567890abcdef"


def setup():
    _, catalog, registry = build_hr_environment()
    signer = TaskContextSigner(SECRET)
    broker = PBMEBroker(
        signer=signer,
        catalog=catalog,
        registry=registry,
        planner=DeterministicInformationPlanner(),
    )
    return signer, broker


def token(signer, goal, purpose):
    return signer.issue(
        task_id="t1",
        user_goal=goal,
        approved_purpose=purpose,
        actor_id="u1",
    )


def test_overbroad_raw_call_is_rerouted_to_aggregate_tool():
    signer, broker = setup()
    result = broker.execute(
        task_token=token(
            signer,
            "Which department had the highest turnover in 2026?",
            "workforce_analytics",
        ),
        proposed_call=ProposedToolCall(
            "get_employee_data",
            {
                "fields": [
                    "employee_id", "name", "ssn", "salary",
                    "department", "termination_date", "email",
                ],
                "year": 2026,
            },
        ),
    )
    assert result.enforcement.selected_tool == "turnover_by_department"
    assert result.enforcement.decision.value == "reroute"
    assert result.enforcement.released_fields == [
        "department", "turnover_count"
    ]
    assert all(
        set(row) == {"department", "turnover_count"}
        for row in result.data
    )


def test_salary_task_denied_for_wrong_purpose():
    signer, broker = setup()
    with pytest.raises(PBMEDenied):
        broker.execute(
            task_token=token(
                signer,
                "Show average salary by department",
                "workforce_analytics",
            ),
            proposed_call=ProposedToolCall(
                "get_employee_data",
                {"fields": ["name", "ssn", "salary", "department"]},
            ),
        )


def test_salary_task_uses_aggregate_when_authorized():
    signer, broker = setup()
    result = broker.execute(
        task_token=token(
            signer,
            "Show average salary by department",
            "compensation_analysis",
        ),
        proposed_call=ProposedToolCall(
            "get_employee_data",
            {"fields": ["name", "ssn", "salary", "department"]},
        ),
    )
    assert result.enforcement.selected_tool == "average_salary_by_department"
    assert result.enforcement.released_fields == [
        "department", "average_salary"
    ]


def test_raw_fallback_projects_minimum_fields():
    signer, broker = setup()
    result = broker.execute(
        task_token=token(
            signer,
            "List names of employees terminated in 2026",
            "hr_operations",
        ),
        proposed_call=ProposedToolCall(
            "get_employee_data",
            {
                "fields": [
                    "name", "ssn", "salary", "department",
                    "termination_date", "email",
                ],
                "year": 2026,
            },
        ),
    )
    assert result.enforcement.selected_tool == "get_employee_data"
    assert result.enforcement.executed_arguments["fields"] == [
        "name", "termination_date"
    ]
    assert all(
        set(row) <= {"name", "termination_date"}
        for row in result.data
    )
