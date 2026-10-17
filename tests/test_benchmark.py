from pbme.benchmark.generate import generate_scenarios
from pbme.benchmark.runner import run_benchmark


def test_generator_builds_500_scenarios():
    scenarios = generate_scenarios()
    assert len(scenarios) == 500
    assert {s.domain for s in scenarios} == {
        "hr", "support", "finance", "documents"
    }
    assert {s.variant for s in scenarios} == {
        "clean",
        "overbroad_fields",
        "safer_tool_available",
        "wrong_purpose",
        "adversarial_smuggling",
    }


def test_small_benchmark_runs_all_systems():
    scenarios = generate_scenarios()[:10]
    results, summary = run_benchmark(
        scenarios,
        repeats=1,
    )
    assert len(results) == 10 * 6
    assert "pbme_full" in summary
    assert "permissive" in summary


def test_pbme_full_reduces_exposure_on_overbroad_case():
    scenarios = [
        s for s in generate_scenarios()
        if s.domain == "hr"
        and s.capability == "turnover_by_department"
        and s.variant == "overbroad_fields"
    ][:1]
    results, _ = run_benchmark(
        scenarios,
        systems=["permissive", "pbme_full"],
        repeats=1,
    )
    by_system = {r.system: r for r in results}
    assert (
        by_system["pbme_full"].exposure_cost
        < by_system["permissive"].exposure_cost
    )
