from __future__ import annotations

import argparse
import json
from pathlib import Path

from .broker_runner import run_broker_validation
from .generate import write_jsonl
from .e3 import write_e3_jsonl
from .reporting import load_run_results, write_breakdown_reports
from .runner import load_jsonl, run_benchmark


def _csv_list(value: str) -> list[str]:
    return [item.strip() for item in value.split(",") if item.strip()]


def main():
    parser = argparse.ArgumentParser(
        description="PBME benchmark, broker validation, and LLM E3 harness"
    )
    sub = parser.add_subparsers(dest="command", required=True)

    gen = sub.add_parser("generate", help="Generate the 500-scenario JSONL set")
    gen.add_argument("--out", default="benchmark/scenarios_500.jsonl")

    e3 = sub.add_parser(
        "generate-e3",
        help="Generate the canonical frozen 200-scenario E3 LLM benchmark",
    )
    e3.add_argument("--out", default="benchmark/e3/scenarios.jsonl")
    e3.add_argument("--manifest", default="benchmark/e3/manifest.json")

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

    llm = sub.add_parser(
        "llm-run",
        help=(
            "E3: ask a real LLM to propose a tool call, then replay the "
            "same proposal through direct execution and PBME"
        ),
    )
    llm.add_argument("--scenarios", default="benchmark/e3/scenarios.jsonl")
    llm.add_argument(
        "--provider",
        default="openai",
        choices=("openai", "openrouter"),
        help="LLM proposal provider: openai or openrouter",
    )
    llm.add_argument("--model", default="gpt-6-luna")
    llm.add_argument("--repeats", type=int, default=1)
    llm.add_argument(
        "--modes",
        default="full_registry,raw_only",
        help="Comma-separated: full_registry,raw_only",
    )
    llm.add_argument(
        "--variants",
        default="all",
        help="Comma-separated E3 variants; default is the complete frozen E3 set.",
    )
    llm.add_argument("--limit", type=int, default=None)
    llm.add_argument("--out-dir", default="benchmark/llm_results")
    llm.add_argument(
        "--reasoning-effort",
        default="none",
        choices=("omit", "none", "low", "medium", "high", "xhigh", "max"),
        help=(
            "Reasoning effort sent to the provider. Use 'omit' to leave the "
            "reasoning parameter out entirely for models that do not support it."
        ),
    )
    llm.add_argument(
        "--openrouter-provider",
        default=None,
        help=(
            "Optional OpenRouter upstream provider slug to prefer/pin "
            "(for example, deepinfra)."
        ),
    )
    llm.add_argument(
        "--disable-provider-fallbacks",
        action="store_true",
        help=(
            "OpenRouter only: disable fallback to other upstream providers. "
            "For reproducible paper runs, combine this with --openrouter-provider."
        ),
    )
    llm.add_argument(
        "--openrouter-require-parameters",
        action="store_true",
        help=(
            "OpenRouter only: route only to endpoints that advertise support for "
            "the Chat Completions parameters used by E3."
        ),
    )
    llm.add_argument("--max-output-tokens", type=int, default=1024)
    llm.add_argument("--timeout", type=float, default=60.0)
    llm.add_argument(
        "--no-resume",
        action="store_true",
        help="Ignore the proposal cache and make fresh model calls",
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

    if args.command == "generate-e3":
        count = write_e3_jsonl(args.out, manifest_path=args.manifest)
        print(json.dumps({
            "generated": count,
            "path": str(Path(args.out)),
            "manifest": str(Path(args.manifest)),
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
        if args.command == "llm-run" and scenarios_path == Path("benchmark/e3/scenarios.jsonl"):
            write_e3_jsonl(scenarios_path)
        else:
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

    if args.command == "llm-run":
        from pbme.llm_agent import (
            OpenAIResponsesToolProposer,
            OpenRouterChatToolProposer,
        )
        from .llm_runner import run_llm_evaluation

        reasoning_effort = (
            None if args.reasoning_effort == "omit" else args.reasoning_effort
        )
        if args.provider == "openrouter":
            proposer = OpenRouterChatToolProposer(
                model=args.model,
                reasoning_effort=reasoning_effort,
                max_output_tokens=args.max_output_tokens,
                timeout=args.timeout,
                upstream_provider=args.openrouter_provider,
                allow_fallbacks=not args.disable_provider_fallbacks,
                require_parameters=args.openrouter_require_parameters,
            )
        else:
            if (
                args.openrouter_provider
                or args.disable_provider_fallbacks
                or args.openrouter_require_parameters
            ):
                parser.error(
                    "OpenRouter routing options require --provider openrouter"
                )
            proposer = OpenAIResponsesToolProposer(
                model=args.model,
                reasoning_effort=reasoning_effort,
                max_output_tokens=args.max_output_tokens,
                timeout=args.timeout,
            )
        _, summary = run_llm_evaluation(
            scenarios,
            proposer=proposer,
            repeats=args.repeats,
            modes=tuple(_csv_list(args.modes)),
            variants=tuple(_csv_list(args.variants)),
            limit=args.limit,
            out_dir=args.out_dir,
            resume=not args.no_resume,
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
