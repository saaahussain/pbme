from pbme.benchmark.broker_runner import run_broker_validation
from pbme.benchmark.generate import generate_scenarios


def _one(domain: str, capability: str, variant: str):
    return next(
        s for s in generate_scenarios()
        if s.domain == domain
        and s.capability == capability
        and s.variant == variant
    )


def test_real_broker_full_registry_agrees_across_all_domains():
    scenarios = [
        _one("hr", "turnover_by_department", "overbroad_fields"),
        _one("support", "total_sales", "adversarial_smuggling"),
        _one("finance", "spend_by_category", "safer_tool_available"),
        _one("documents", "count_by_department", "overbroad_fields"),
    ]
    results, summary = run_broker_validation(
        scenarios,
        repeats=1,
        modes=("full_registry",),
        inject_over_return=True,
    )
    assert len(results) == 4
    assert summary["overall"]["task_success_rate"] == 1.0
    assert summary["overall"]["simulator_policy_agreement"] == 1.0
    assert summary["overall"]["selected_tool_agreement"] == 1.0
    assert summary["overall"]["released_field_agreement"] == 1.0
    assert summary["overall"]["response_filter_accuracy"] == 1.0
    assert summary["overall"]["audit_completeness"] == 1.0


def test_real_broker_raw_only_proves_field_rewriting():
    scenario = _one(
        "hr", "turnover_by_department", "overbroad_fields"
    )
    results, summary = run_broker_validation(
        [scenario],
        repeats=1,
        modes=("raw_only",),
        inject_over_return=True,
    )
    assert len(results) == 1
    assert results[0].field_rewrite_correct is True
    assert results[0].response_filter_correct is True
    assert results[0].task_success is True
    assert summary["overall"]["field_rewrite_accuracy"] == 1.0


def test_real_broker_audits_expected_denial():
    scenario = _one(
        "finance", "spend_by_category", "wrong_purpose"
    )
    results, summary = run_broker_validation(
        [scenario],
        repeats=1,
        modes=("full_registry",),
        inject_over_return=True,
    )
    assert results[0].broker_decision == "deny"
    assert results[0].policy_correct is True
    assert results[0].audit_complete is True
    assert summary["overall"]["policy_accuracy"] == 1.0
