from pbme.llm_planner import StructuredLLMPlanner
from pbme.models import TaskContext


def test_llm_cannot_invent_required_fields():
    def fake_model(prompt):
        return {
            "capability": "turnover_by_department",
            "parameters": {"year": 2026},
            "required_fields": ["ssn", "salary"],
            "confidence": 0.9,
        }

    ctx = TaskContext(
        task_id="t",
        user_goal="turnover by department 2026",
        approved_purpose="workforce_analytics",
        actor_id="u",
        issued_at=1,
        expires_at=9999999999,
    )
    plan = StructuredLLMPlanner(fake_model).plan(ctx)
    assert plan.required_fields == ["department", "termination_date"]
