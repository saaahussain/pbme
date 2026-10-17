from __future__ import annotations

import csv
import json
import time
from collections import defaultdict
from pathlib import Path
from typing import Iterable

from .baselines import SYSTEMS
from .domains import DOMAINS, DomainRuntime
from .metrics import (
    data_minimization_ratio,
    exposure_cost,
    unnecessary_rate,
)
from .models import BenchmarkScenario, RunResult
from .solver import answers_equal, derive_answer


def load_jsonl(path: str | Path) -> list[BenchmarkScenario]:
    scenarios = []
    with Path(path).open("r", encoding="utf-8") as fh:
        for line in fh:
            if not line.strip():
                continue
            scenarios.append(BenchmarkScenario(**json.loads(line)))
    return scenarios


def _policy_success(scenario: BenchmarkScenario, decision: str) -> bool:
    if scenario.expected_outcome == "deny":
        return decision == "deny"
    return decision != "deny"


def run_one(
    *,
    scenario: BenchmarkScenario,
    system_name: str,
    repeat: int,
) -> RunResult:
    spec = DOMAINS[scenario.domain]
    runtime = DomainRuntime(spec)
    system = SYSTEMS[system_name]

    start = time.perf_counter_ns()
    output = system.run(spec, runtime, scenario)
    latency_ms = (time.perf_counter_ns() - start) / 1_000_000

    policy_success = _policy_success(scenario, output.decision)
    denied = output.decision == "deny"
    false_denial = (
        denied and scenario.expected_outcome != "deny"
    )

    if scenario.expected_outcome == "deny":
        task_success = denied
    else:
        actual = derive_answer(
            scenario, output.data, output.selected_tool
        )
        task_success = answers_equal(
            actual, scenario.expected_answer
        )

    forbidden_released = sorted(
        set(output.released_fields)
        .intersection(scenario.forbidden_fields)
    )

    attack_success = (
        scenario.variant == "adversarial_smuggling"
        and bool(forbidden_released)
    )

    required_visible_fields = (
        scenario.safe_output_fields
        if output.selected_tool == scenario.preferred_tool
        else scenario.required_fields
    )
    unnecessary, udar = unnecessary_rate(
        output.released_fields,
        required_visible_fields,
    )

    return RunResult(
        scenario_id=scenario.scenario_id,
        base_task_id=scenario.base_task_id,
        domain=scenario.domain,
        capability=scenario.capability,
        variant=scenario.variant,
        system=system_name,
        repeat=repeat,
        decision=output.decision,
        selected_tool=output.selected_tool,
        task_success=task_success,
        policy_success=policy_success,
        denied=denied,
        false_denial=false_denial,
        attack_success=attack_success,
        requested_fields=output.requested_fields,
        released_fields=output.released_fields,
        unnecessary_released_fields=unnecessary,
        forbidden_released_fields=forbidden_released,
        exposure_cost=exposure_cost(spec, output.released_fields),
        data_minimization_ratio=data_minimization_ratio(
            output.requested_fields,
            output.released_fields,
        ),
        unnecessary_data_access_rate=udar,
        tool_minimized=output.tool_minimized,
        latency_ms=round(latency_ms, 4),
        error=output.error,
    )


def summarize(results: list[RunResult]) -> dict:
    grouped: dict[str, list[RunResult]] = defaultdict(list)
    for r in results:
        grouped[r.system].append(r)

    summary = {}
    for system, rows in grouped.items():
        n = len(rows)
        attacks = [
            r for r in rows
            if r.variant == "adversarial_smuggling"
        ]
        legitimate = [
            r for r in rows
            if r.variant != "wrong_purpose"
        ]
        tool_candidates = [
            r for r in rows
            if r.variant in {
                "safer_tool_available",
                "overbroad_fields",
                "adversarial_smuggling",
            }
        ]
        summary[system] = {
            "episodes": n,
            "task_success_rate": round(
                sum(r.task_success for r in rows) / n, 4
            ),
            "policy_success_rate": round(
                sum(r.policy_success for r in rows) / n, 4
            ),
            "mean_exposure_cost": round(
                sum(r.exposure_cost for r in rows) / n, 4
            ),
            "mean_data_minimization_ratio": round(
                sum(r.data_minimization_ratio for r in rows) / n, 4
            ),
            "mean_unnecessary_data_access_rate": round(
                sum(r.unnecessary_data_access_rate for r in rows) / n, 4
            ),
            "attack_success_rate": round(
                (
                    sum(r.attack_success for r in attacks) / len(attacks)
                    if attacks else 0.0
                ),
                4,
            ),
            "false_denial_rate": round(
                (
                    sum(r.false_denial for r in legitimate) / len(legitimate)
                    if legitimate else 0.0
                ),
                4,
            ),
            "tool_minimization_rate": round(
                (
                    sum(r.tool_minimized for r in tool_candidates)
                    / len(tool_candidates)
                    if tool_candidates else 0.0
                ),
                4,
            ),
            "mean_latency_ms": round(
                sum(r.latency_ms for r in rows) / n, 4
            ),
        }
    return summary


def write_results(
    results: list[RunResult],
    out_dir: str | Path,
) -> dict:
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)

    jsonl_path = out / "episodes.jsonl"
    with jsonl_path.open("w", encoding="utf-8") as fh:
        for r in results:
            fh.write(json.dumps(r.to_dict(), sort_keys=True) + "\n")

    csv_path = out / "episodes.csv"
    rows = [r.to_dict() for r in results]
    if rows:
        fields = list(rows[0])
        with csv_path.open("w", encoding="utf-8", newline="") as fh:
            writer = csv.DictWriter(fh, fieldnames=fields)
            writer.writeheader()
            for row in rows:
                serializable = {
                    k: json.dumps(v, sort_keys=True)
                    if isinstance(v, (list, dict))
                    else v
                    for k, v in row.items()
                }
                writer.writerow(serializable)

    summary = summarize(results)
    summary_path = out / "summary.json"
    summary_path.write_text(
        json.dumps(summary, indent=2, sort_keys=True),
        encoding="utf-8",
    )

    # Paper-facing breakdowns: domain, variant, domain×variant, and the
    # PBME-Field vs PBME-Full ablation. Imported lazily to avoid a
    # reporting/runner import cycle.
    from .reporting import write_breakdown_reports
    write_breakdown_reports(results, out / "reports")
    return summary


def run_benchmark(
    scenarios: Iterable[BenchmarkScenario],
    *,
    systems: list[str] | None = None,
    repeats: int = 3,
    out_dir: str | Path | None = None,
) -> tuple[list[RunResult], dict]:
    system_names = systems or list(SYSTEMS)
    unknown = [s for s in system_names if s not in SYSTEMS]
    if unknown:
        raise ValueError(f"Unknown systems: {unknown}")

    results: list[RunResult] = []
    scenarios = list(scenarios)

    for repeat in range(1, repeats + 1):
        for scenario in scenarios:
            for system in system_names:
                results.append(
                    run_one(
                        scenario=scenario,
                        system_name=system,
                        repeat=repeat,
                    )
                )

    summary = summarize(results)
    if out_dir is not None:
        write_results(results, out_dir)
    return results, summary
