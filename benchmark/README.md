# PBME Evaluation Harness

This repository contains two deliberately separate evaluation tracks.

## E1 — Controlled policy simulation

The generator creates:

- 4 domains
- 25 base tasks per domain
- 100 base tasks total
- 5 variants per base task
- 500 scenarios total

Systems:

1. `permissive`
2. `rbac_only`
3. `static_masking`
4. `ares_like`
5. `pbme_field`
6. `pbme_full`

With three repeats:

```text
500 scenarios × 6 systems × 3 repeats = 9,000 episodes
```

Generate and run:

```bash
pbme-benchmark generate
pbme-benchmark run --repeats 3
```

Outputs:

```text
benchmark/results/
  episodes.jsonl
  episodes.csv
  summary.json
  reports/
    domain_breakdown.csv
    variant_breakdown.csv
    domain_variant_breakdown.csv
    ablation_breakdown.csv
    ... matching JSON files
```

The policy simulation does **not** invoke `PBMEBroker`. It isolates the
behavior of the six evaluation policies under identical deterministic ground
truth.

## E2 — Real PBMEBroker integration validation

The broker runner executes the same scenario definitions through the actual
pipeline:

```text
signed TaskContext
    -> planner
    -> PlanVerifier
    -> governance policy
    -> tool optimizer
    -> RequestRewriter
    -> actual SQLite backend
    -> ResponseFilter
    -> JsonlAuditLog
```

Run:

```bash
pbme-benchmark broker-run --repeats 3
```

Two modes are used:

- `full_registry` — all safe aggregate tools are available; validates tool
  minimization and rerouting.
- `raw_only` — only the domain raw-record tool is available; forces field
  projection and validates request rewriting.

The broker validation also injects one intentional undeclared field into
backend responses. Correct execution requires the real `ResponseFilter` to
remove it before the result reaches the caller.

With the full 500 scenarios and three repeats, the default run produces:

```text
full_registry: 500 × 3 = 1,500 episodes
raw_only:      400 × 3 = 1,200 episodes
---------------------------------------
total:                    2,700 episodes
```

`raw_only` skips clean scenarios whose proposed tool is already a safe
aggregate tool.

Outputs:

```text
benchmark/broker_results/
  broker_episodes.jsonl
  broker_episodes.csv
  broker_summary.json
  broker_domain_breakdown.csv
  broker_variant_breakdown.csv
```

Broker metrics include:

- task success
- expected-policy accuracy
- simulator/broker allow-deny agreement
- exact decision agreement
- selected-tool agreement
- released-field agreement
- field-rewrite accuracy
- response-filter accuracy
- audit completeness
- exposure cost
- broker latency

## Ground truth

Every JSONL scenario contains:

- `required_fields` — minimum raw fields when a raw-record tool is necessary
- `safe_output_fields` — minimum agent-visible fields for the preferred safe tool
- `optional_fields`
- `forbidden_fields`
- `preferred_tool`
- `allowed_tools`
- `expected_answer`
- `expected_outcome`

The ground truth is deterministic and generated from the domain specification,
not judged by the system under test.

## Variants

- `clean`
- `overbroad_fields`
- `safer_tool_available`
- `wrong_purpose`
- `adversarial_smuggling`

## Reporting

Regenerate paper-facing reports from an existing episode file:

```bash
pbme-benchmark report \
  --episodes benchmark/results/episodes.jsonl \
  --out-dir benchmark/results/reports
```

The ablation report compares `pbme_field` with `pbme_full` overall and
by domain/variant.

## Interpretation boundary

E1 is a **controlled policy simulation**. E2 proves that the implemented broker
realizes those policies in the synthetic environments. Neither E1 nor E2 is an
LLM-in-the-loop benchmark: capability ground truth and task schemas are
controlled by the benchmark. Claims about real model tool-selection behavior
require a separate E3 model experiment.
