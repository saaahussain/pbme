from pbme.models import TaskContext
from pbme.planner import DeterministicInformationPlanner


def ctx(goal: str):
    return TaskContext(
        task_id="t",
        user_goal=goal,
        approved_purpose="workforce_analytics",
        actor_id="u",
        issued_at=1,
        expires_at=9999999999,
    )


def test_turnover_plan():
    plan = DeterministicInformationPlanner().plan(
        ctx("Which department had the highest turnover in 2026?")
    )
    assert plan.capability == "turnover_by_department"
    assert plan.required_fields == ["department", "termination_date"]
    assert plan.parameters["year"] == 2026


def test_salary_plan():
    plan = DeterministicInformationPlanner().plan(
        ctx("Show average salary by department")
    )
    assert plan.capability == "average_salary_by_department"
    assert plan.required_fields == ["department", "salary"]
