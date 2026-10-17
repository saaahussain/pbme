from __future__ import annotations

import argparse
import json
from pathlib import Path

from .broker_runner import run_broker_validation
from .generate import write_jsonl
from .reporting import load_run_results, write_breakdown_reports
from .runner import load_jsonl, run_benchmark


def _csv_list(value: str) -> list[str]:
    return [item.strip() for item in value.split(",") if item.strip()]


def main():
    parser = argparse.ArgumentParser(
        description="PBME benchmark and real-broker validation harness"
    )
    sub = parser.add_subparsers(dest="command", required=True)

    gen = sub.add_parser("generate", help="Generate the 500-scenario JSONL set")
    gen.add_argument("--out", default="benchmark/scenarios_500.jsonl")

    run = sub.add_parser("run", help="Run the six-way policy simulation")
    run.add_argument("--scenarios", default="benchmark/scenarios_500.jsonl")
    run.add_argument(
        "--systems",
        default=(
            "permissive,rbac_only,static_masking,"
            "ares_like,pbme_field,pbme_full"
        ),
    )
    run.add_argument("--repeats", type=int, default=3)
    run.add_argument("--out-dir", default="benchmark/results")

    broker = sub.add_parser(
        "broker-run",
        help=(
            "Run scenarios through the actual PBMEBroker pipeline and "
            "compare it with the policy simulator"
        ),
    )
    broker.add_argument("--scenarios", default="benchmark/scenarios_500.jsonl")
    broker.add_argument("--repeats", type=int, default=3)
    broker.add_argument(
        "--modes",
        default="full_registry,raw_only",
        help="Comma-separated: full_registry,raw_only",
    )
    broker.add_argument("--limit", type=int, default=None)
    broker.add_argument("--out-dir", default="benchmark/broker_results")
    broker.add_argument(
        "--no-over-return-test",
        action="store_true",
        help="Disable intentional backend over-return injection",
    )

    report = sub.add_parser(
        "report",
        help="Generate domain/variant/ablation reports from episodes.jsonl",
    )
    report.add_argument(
        "--episodes",
        default="benchmark/results/episodes.jsonl",
    )
    report.add_argument("--out-dir", default="benchmark/results/reports")

    args = parser.parse_args()

    if args.command == "generate":
        count = write_jsonl(args.out)
        print(json.dumps({
            "generated": count,
            "path": str(Path(args.out)),
        }, indent=2))
        return

    if args.command == "report":
        results = load_run_results(args.episodes)
        reports = write_breakdown_reports(results, args.out_dir)
        print(json.dumps({
            "episodes": len(results),
            "out_dir": args.out_dir,
            "domain_rows": len(reports["domain"]),
            "variant_rows": len(reports["variant"]),
            "ablation_rows": len(reports["ablation"]),
        }, indent=2))
        return

    scenarios_path = Path(args.scenarios)
    if not scenarios_path.exists():
        write_jsonl(scenarios_path)
    scenarios = load_jsonl(scenarios_path)

    if args.command == "broker-run":
        if args.limit is not None:
            scenarios = scenarios[: args.limit]
        modes = tuple(_csv_list(args.modes))
        _, summary = run_broker_validation(
            scenarios,
            repeats=args.repeats,
            modes=modes,
            inject_over_return=not args.no_over_return_test,
            out_dir=args.out_dir,
        )
        print(json.dumps(summary, indent=2, sort_keys=True))
        return

    systems = _csv_list(args.systems)
    _, summary = run_benchmark(
        scenarios,
        systems=systems,
        repeats=args.repeats,
        out_dir=args.out_dir,
    )
    print(json.dumps(summary, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
