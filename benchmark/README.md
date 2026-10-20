# PBME Evaluation Harness

PBME uses three complementary evaluation tracks. They intentionally answer different
questions and should not be merged into one undifferentiated benchmark.

## E1 — Controlled policy simulation

E1 evaluates six policy strategies under deterministic benchmark ground truth.

- 4 domains
- 25 base tasks per domain
- 100 base tasks
- 5 variants per base task
- 500 scenarios
- 6 systems
- 3 deterministic repetitions
- 9,000 episodes

Run:

```bash
pbme-benchmark generate
pbme-benchmark run --repeats 3
```

Outputs are written under `benchmark/results/`.

E1 does not invoke a real LLM and does not execute the production broker path. It
isolates policy behavior under identical controlled ground truth.

## E2 — PBMEBroker conformance validation

E2 executes benchmark tasks through the actual broker pipeline:

```text
signed TaskContext
    -> planner
    -> PlanVerifier
    -> governance policy
    -> tool optimizer
    -> RequestRewriter
    -> backend
    -> ResponseFilter
    -> audit log
```

Run:

```bash
pbme-benchmark broker-run --repeats 3
```

The default full evaluation produces 2,700 broker executions:

```text
full_registry: 500 x 3 = 1,500
raw_only:      400 x 3 = 1,200
--------------------------------
total:                    2,700
```

Outputs are written under `benchmark/broker_results/`.

E2 establishes implementation conformance within the controlled task family. It is
not an open-domain semantic-planning benchmark.

## E3 — Real-LLM paired evaluation

E3 is the active frozen real-LLM benchmark. Its canonical dataset is:

```text
benchmark/e3/scenarios.jsonl
benchmark/e3/manifest.json
```

Generate it with:

```bash
pbme-benchmark generate-e3
```

Each E3 scenario is assigned exactly one tool mode. Across the 200 scenarios there are
100 `full_registry` and 100 `raw_only` cases. For each model/repeat, the LLM generates
one structured proposal per scenario. The exact same proposal is then replayed through:

```text
same LLM proposal
      /      \
     v        v
llm_direct  llm_pbme
```

This paired design prevents model sampling differences from being mistaken for PBME's
effect.

Run:

```bash
pbme-benchmark llm-run \
  --scenarios benchmark/e3/scenarios.jsonl \
  --model gpt-6-luna \
  --repeats 1 \
  --out-dir benchmark/llm_results/validation_gpt6_luna_r1
```

E3 reports proposal behavior and paired execution outcomes, including:

- scenario success
- task completion on expected-allow scenarios
- policy success
- exposure cost
- unnecessary data access rate (UDAR)
- forbidden field release rate (FFRR)
- attack success rate (ASR)
- false denial rate (FDR)
- request transformation rate
- reroute rate
- tool minimization rate (TMR) over eligible opportunities
- model token counts and latency

For TMR, the denominator is only episodes where a lower-exposure task-compatible
alternative actually exists. `raw_only` episodes therefore have no TMR denominator.
Reroute rate is reported separately over all episodes.

The E3 dataset uses task-relative identifier semantics: signed selector IDs are
preserved as normal tool arguments, while returned field projections are minimized
independently. PBME does not mint or translate enterprise identifiers.

For compatibility with already-created traces, scenario IDs retain the historical
`E3V21-*` prefix and the split string remains `frozen_eval_v2_1`. The repository has
one active E3 benchmark; these strings are stable artifact identifiers, not active
version names.

See `benchmark/e3/README.md` and `docs/LLM_EVALUATION.md` for details.

## Ground truth

Scenario JSONL records include benchmark ground truth such as:

- `required_arguments`
- `required_fields`
- `safe_output_fields`
- `optional_fields`
- `forbidden_fields`
- `preferred_tool`
- `allowed_tools`
- `expected_answer`
- `expected_outcome`

These fields are used by deterministic evaluation and PBME verification as appropriate;
they are not supplied to the E3 LLM as hidden hints.
