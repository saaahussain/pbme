from pbme.benchmark.generate import generate_scenarios
from pbme.benchmark.reporting import ablation_report, grouped_summary
from pbme.benchmark.runner import run_benchmark


def test_domain_variant_and_ablation_reports():
    scenarios = generate_scenarios()[:25]
    results, _ = run_benchmark(
        scenarios,
        systems=["pbme_field", "pbme_full"],
        repeats=1,
    )
    by_domain = grouped_summary(results, ("system", "domain"))
    by_variant = grouped_summary(results, ("system", "variant"))
    ablation = ablation_report(results)
    assert by_domain
    assert by_variant
    assert ablation
    assert any(r["scope_type"] == "overall" for r in ablation)
