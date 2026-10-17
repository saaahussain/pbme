from __future__ import annotations

import csv
import json
from collections import defaultdict
from pathlib import Path
from typing import Any, Iterable

from .models import RunResult


METRICS = (
    "task_success_rate",
    "policy_success_rate",
    "mean_exposure_cost",
    "mean_data_minimization_ratio",
    "mean_unnecessary_data_access_rate",
    "attack_success_rate",
    "false_denial_rate",
    "tool_minimization_rate",
    "mean_latency_ms",
)


def load_run_results(path: str | Path) -> list[RunResult]:
    rows: list[RunResult] = []
    with Path(path).open("r", encoding="utf-8") as fh:
        for line in fh:
            if line.strip():
                rows.append(RunResult(**json.loads(line)))
    return rows


def _aggregate(rows: list[RunResult]) -> dict[str, Any]:
    if not rows:
        return {"episodes": 0}
    n = len(rows)
    attacks = [r for r in rows if r.variant == "adversarial_smuggling"]
    legitimate = [r for r in rows if r.variant != "wrong_purpose"]
    tool_candidates = [
        r for r in rows
        if r.variant in {
            "safer_tool_available",
            "overbroad_fields",
            "adversarial_smuggling",
        }
    ]
    return {
        "episodes": n,
        "task_success_rate": round(sum(r.task_success for r in rows) / n, 4),
        "policy_success_rate": round(sum(r.policy_success for r in rows) / n, 4),
        "mean_exposure_cost": round(sum(r.exposure_cost for r in rows) / n, 4),
        "mean_data_minimization_ratio": round(
            sum(r.data_minimization_ratio for r in rows) / n, 4
        ),
        "mean_unnecessary_data_access_rate": round(
            sum(r.unnecessary_data_access_rate for r in rows) / n, 4
        ),
        "attack_success_rate": round(
            sum(r.attack_success for r in attacks) / len(attacks)
            if attacks else 0.0,
            4,
        ),
        "false_denial_rate": round(
            sum(r.false_denial for r in legitimate) / len(legitimate)
            if legitimate else 0.0,
            4,
        ),
        "tool_minimization_rate": round(
            sum(r.tool_minimized for r in tool_candidates) / len(tool_candidates)
            if tool_candidates else 0.0,
            4,
        ),
        "mean_latency_ms": round(sum(r.latency_ms for r in rows) / n, 4),
    }


def grouped_summary(
    results: Iterable[RunResult],
    group_fields: tuple[str, ...],
) -> list[dict[str, Any]]:
    groups: dict[tuple[Any, ...], list[RunResult]] = defaultdict(list)
    for row in results:
        key = tuple(getattr(row, field) for field in group_fields)
        groups[key].append(row)

    output = []
    for key, rows in sorted(groups.items(), key=lambda item: item[0]):
        labels = dict(zip(group_fields, key))
        output.append({**labels, **_aggregate(rows)})
    return output


def ablation_report(results: Iterable[RunResult]) -> list[dict[str, Any]]:
    rows = list(results)
    output = []
    scopes = [("overall", None)]
    scopes.extend(("domain", d) for d in sorted({r.domain for r in rows}))
    scopes.extend(("variant", v) for v in sorted({r.variant for r in rows}))

    for scope_type, scope_value in scopes:
        scoped = rows
        if scope_type == "domain":
            scoped = [r for r in rows if r.domain == scope_value]
        elif scope_type == "variant":
            scoped = [r for r in rows if r.variant == scope_value]

        field_rows = [r for r in scoped if r.system == "pbme_field"]
        full_rows = [r for r in scoped if r.system == "pbme_full"]
        if not field_rows or not full_rows:
            continue
        field_metrics = _aggregate(field_rows)
        full_metrics = _aggregate(full_rows)
        row = {
            "scope_type": scope_type,
            "scope_value": scope_value or "all",
            "pbme_field_episodes": field_metrics["episodes"],
            "pbme_full_episodes": full_metrics["episodes"],
        }
        for metric in METRICS:
            row[f"field_{metric}"] = field_metrics[metric]
            row[f"full_{metric}"] = full_metrics[metric]
            row[f"delta_full_minus_field_{metric}"] = round(
                full_metrics[metric] - field_metrics[metric], 4
            )
        output.append(row)
    return output


def _write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    if not rows:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    fields = list(rows[0])
    with path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def write_breakdown_reports(
    results: Iterable[RunResult],
    out_dir: str | Path,
) -> dict[str, list[dict[str, Any]]]:
    rows = list(results)
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)

    reports = {
        "domain": grouped_summary(rows, ("system", "domain")),
        "variant": grouped_summary(rows, ("system", "variant")),
        "domain_variant": grouped_summary(
            rows, ("system", "domain", "variant")
        ),
        "ablation": ablation_report(rows),
    }

    for name, data in reports.items():
        _write_csv(out / f"{name}_breakdown.csv", data)
        (out / f"{name}_breakdown.json").write_text(
            json.dumps(data, indent=2, sort_keys=True),
            encoding="utf-8",
        )
    return reports
