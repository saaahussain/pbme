from __future__ import annotations

import csv
import json
import time
from collections import defaultdict
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Iterable

from pbme.broker import PBMEDenied
from pbme.models import ProposedToolCall

from .baselines import PBMEFieldSystem, PBMEFullSystem
from .broker_adapter import build_benchmark_broker
from .domains import DOMAINS, DomainRuntime
from .metrics import exposure_cost
from .models import BenchmarkScenario
from .solver import answers_equal, derive_answer


BROKER_SECRET = "pbme-benchmark-broker-secret"


@dataclass
class BrokerValidationResult:
    scenario_id: str
    base_task_id: str
    domain: str
    capability: str
    variant: str
    mode: str
    repeat: int
    broker_decision: str
    simulator_decision: str
    expected_outcome: str
    policy_correct: bool
    simulator_policy_agreement: bool
    exact_decision_agreement: bool
    selected_tool: str | None
    simulator_selected_tool: str | None
    selected_tool_agreement: bool
    released_fields: list[str]
    simulator_released_fields: list[str]
    released_field_agreement: bool
    field_rewrite_correct: bool | None
    response_filter_correct: bool | None
    audit_complete: bool
    task_success: bool
    exposure_cost: float
    latency_ms: float
    error: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _output_fields(data: Any) -> list[str]:
    keys: set[str] = set()
    if isinstance(data, list):
        for item in data:
            if isinstance(item, dict):
                keys.update(item)
    elif isinstance(data, dict):
        keys.update(data)
    return sorted(keys)


def _is_deny(decision: str) -> bool:
    return decision == "deny"


def _audit_complete(events: list[dict]) -> bool:
    if len(events) != 1:
        return False
    event = events[0]
    required = {
        "timestamp_utc",
        "decision",
        "context",
        "proposed_call",
        "released_fields",
        "removed_fields",
        "exposure_before",
        "exposure_after",
        "rationale",
        "planner",
    }
    return required.issubset(event) and bool(event.get("rationale"))


def _injection_field(scenario: BenchmarkScenario) -> str | None:
    spec = DOMAINS[scenario.domain]
    preferred = list(scenario.forbidden_fields)
    preferred.extend(
        field for field in spec.all_fields
        if field not in scenario.required_fields
    )
    for field in preferred:
        if field in spec.field_policies:
            return field
    return None


def _simulator_output(
    scenario: BenchmarkScenario,
    *,
    mode: str,
):
    spec = DOMAINS[scenario.domain]
    runtime = DomainRuntime(spec)
    system = (
        PBMEFullSystem()
        if mode == "full_registry"
        else PBMEFieldSystem()
    )
    return system.run(spec, runtime, scenario)


def run_broker_one(
    *,
    scenario: BenchmarkScenario,
    mode: str,
    repeat: int,
    inject_over_return: bool = True,
) -> BrokerValidationResult:
    spec = DOMAINS[scenario.domain]

    if mode == "raw_only" and scenario.proposed_tool != spec.raw_tool:
        raise ValueError(
            "raw_only validation requires a scenario whose proposed tool is "
            f"the domain raw tool ({spec.raw_tool})"
        )

    injected = _injection_field(scenario) if inject_over_return else None
    broker, signer, _ = build_benchmark_broker(
        spec,
        secret=BROKER_SECRET,
        mode=mode,
        injected_over_return_field=injected,
    )

    token = signer.issue(
        task_id=f"broker-{scenario.scenario_id}-{repeat}",
        user_goal=scenario.goal,
        approved_purpose=scenario.purpose,
        actor_id="benchmark-broker-user",
        task_parameters=dict(scenario.parameters),
    )
    proposed = ProposedToolCall(
        tool_name=scenario.proposed_tool,
        arguments=dict(scenario.proposed_arguments),
    )

    simulator = _simulator_output(scenario, mode=mode)
    # Compare the broker against the simulator's *policy release schema*, not
    # only keys observed in returned rows. Empty query results legitimately
    # contain no keys, but the simulated policy still authorized a schema.
    if simulator.decision == "deny":
        simulator_policy_fields: list[str] = []
    elif mode == "full_registry":
        simulator_policy_fields = list(
            spec.capabilities[scenario.capability].safe_output_fields
        )
    else:
        simulator_policy_fields = list(scenario.required_fields)

    start = time.perf_counter_ns()
    data = None
    error = None
    record = None
    try:
        result = broker.execute(task_token=token, proposed_call=proposed)
        data = result.data
        record = result.enforcement
        broker_decision = record.decision.value
    except PBMEDenied as exc:
        error = str(exc)
        record = exc.record
        broker_decision = "deny"
    latency_ms = (time.perf_counter_ns() - start) / 1_000_000

    if record is None:
        raise RuntimeError(
            "Broker validation received a denial without an enforcement record"
        )

    released = list(record.released_fields)
    simulator_released = simulator_policy_fields

    expected_deny = scenario.expected_outcome == "deny"
    policy_correct = (
        _is_deny(broker_decision) == expected_deny
    )
    simulator_policy_agreement = (
        _is_deny(broker_decision) == _is_deny(simulator.decision)
    )

    if expected_deny:
        task_success = broker_decision == "deny"
    elif broker_decision == "deny":
        task_success = False
    else:
        actual = derive_answer(scenario, data, record.selected_tool)
        task_success = answers_equal(actual, scenario.expected_answer)

    if broker_decision == "deny":
        response_filter_correct = None
    elif injected is None:
        response_filter_correct = None
    else:
        response_filter_correct = injected not in _output_fields(data)

    if mode == "raw_only" and broker_decision != "deny":
        field_rewrite_correct = (
            record.executed_arguments.get("fields")
            == list(scenario.required_fields)
        )
    else:
        field_rewrite_correct = None

    return BrokerValidationResult(
        scenario_id=scenario.scenario_id,
        base_task_id=scenario.base_task_id,
        domain=scenario.domain,
        capability=scenario.capability,
        variant=scenario.variant,
        mode=mode,
        repeat=repeat,
        broker_decision=broker_decision,
        simulator_decision=simulator.decision,
        expected_outcome=scenario.expected_outcome,
        policy_correct=policy_correct,
        simulator_policy_agreement=simulator_policy_agreement,
        exact_decision_agreement=(broker_decision == simulator.decision),
        selected_tool=record.selected_tool,
        simulator_selected_tool=simulator.selected_tool,
        selected_tool_agreement=(record.selected_tool == simulator.selected_tool),
        released_fields=sorted(released),
        simulator_released_fields=sorted(simulator_released),
        released_field_agreement=(set(released) == set(simulator_released)),
        field_rewrite_correct=field_rewrite_correct,
        response_filter_correct=response_filter_correct,
        audit_complete=_audit_complete(broker.audit.events),
        task_success=task_success,
        exposure_cost=exposure_cost(spec, released),
        latency_ms=round(latency_ms, 4),
        error=error,
    )


def _rate(rows: list[BrokerValidationResult], attr: str) -> float | None:
    values = [getattr(r, attr) for r in rows if getattr(r, attr) is not None]
    if not values:
        return None
    return round(sum(bool(v) for v in values) / len(values), 4)


def _aggregate(rows: list[BrokerValidationResult]) -> dict[str, Any]:
    if not rows:
        return {"episodes": 0}
    return {
        "episodes": len(rows),
        "task_success_rate": _rate(rows, "task_success"),
        "policy_accuracy": _rate(rows, "policy_correct"),
        "simulator_policy_agreement": _rate(
            rows, "simulator_policy_agreement"
        ),
        "exact_decision_agreement": _rate(
            rows, "exact_decision_agreement"
        ),
        "selected_tool_agreement": _rate(
            rows, "selected_tool_agreement"
        ),
        "released_field_agreement": _rate(
            rows, "released_field_agreement"
        ),
        "field_rewrite_accuracy": _rate(
            rows, "field_rewrite_correct"
        ),
        "response_filter_accuracy": _rate(
            rows, "response_filter_correct"
        ),
        "audit_completeness": _rate(rows, "audit_complete"),
        "mean_exposure_cost": round(
            sum(r.exposure_cost for r in rows) / len(rows), 4
        ),
        "mean_latency_ms": round(
            sum(r.latency_ms for r in rows) / len(rows), 4
        ),
    }


def summarize_broker(
    results: list[BrokerValidationResult],
) -> dict[str, Any]:
    by_mode: dict[str, list[BrokerValidationResult]] = defaultdict(list)
    by_domain: dict[tuple[str, str], list[BrokerValidationResult]] = defaultdict(list)
    by_variant: dict[tuple[str, str], list[BrokerValidationResult]] = defaultdict(list)

    for row in results:
        by_mode[row.mode].append(row)
        by_domain[(row.mode, row.domain)].append(row)
        by_variant[(row.mode, row.variant)].append(row)

    return {
        "overall": _aggregate(results),
        "by_mode": {
            mode: _aggregate(rows)
            for mode, rows in sorted(by_mode.items())
        },
        "by_domain": {
            f"{mode}:{domain}": _aggregate(rows)
            for (mode, domain), rows in sorted(by_domain.items())
        },
        "by_variant": {
            f"{mode}:{variant}": _aggregate(rows)
            for (mode, variant), rows in sorted(by_variant.items())
        },
    }


def _write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    if not rows:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    fields = list(rows[0])
    with path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=fields)
        writer.writeheader()
        for row in rows:
            writer.writerow({
                key: json.dumps(value, sort_keys=True)
                if isinstance(value, (list, dict))
                else value
                for key, value in row.items()
            })


def write_broker_results(
    results: list[BrokerValidationResult],
    out_dir: str | Path,
) -> dict[str, Any]:
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)

    with (out / "broker_episodes.jsonl").open("w", encoding="utf-8") as fh:
        for row in results:
            fh.write(json.dumps(row.to_dict(), sort_keys=True) + "\n")

    _write_csv(out / "broker_episodes.csv", [r.to_dict() for r in results])

    summary = summarize_broker(results)
    (out / "broker_summary.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True),
        encoding="utf-8",
    )

    domain_rows = []
    for key, metrics in summary["by_domain"].items():
        mode, domain = key.split(":", 1)
        domain_rows.append({"mode": mode, "domain": domain, **metrics})
    _write_csv(out / "broker_domain_breakdown.csv", domain_rows)

    variant_rows = []
    for key, metrics in summary["by_variant"].items():
        mode, variant = key.split(":", 1)
        variant_rows.append({"mode": mode, "variant": variant, **metrics})
    _write_csv(out / "broker_variant_breakdown.csv", variant_rows)

    return summary


def run_broker_validation(
    scenarios: Iterable[BenchmarkScenario],
    *,
    repeats: int = 3,
    modes: tuple[str, ...] = ("full_registry", "raw_only"),
    inject_over_return: bool = True,
    out_dir: str | Path | None = None,
) -> tuple[list[BrokerValidationResult], dict[str, Any]]:
    scenarios = list(scenarios)
    results: list[BrokerValidationResult] = []

    for repeat in range(1, repeats + 1):
        for scenario in scenarios:
            for mode in modes:
                if (
                    mode == "raw_only"
                    and scenario.proposed_tool
                    != DOMAINS[scenario.domain].raw_tool
                ):
                    continue
                results.append(
                    run_broker_one(
                        scenario=scenario,
                        mode=mode,
                        repeat=repeat,
                        inject_over_return=inject_over_return,
                    )
                )

    summary = summarize_broker(results)
    if out_dir is not None:
        write_broker_results(results, out_dir)
    return results, summary
