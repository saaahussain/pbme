# PBME E3 — Frozen Real-LLM Benchmark

E3 is the canonical 200-scenario benchmark used for the real-LLM paired evaluation.
The benchmark is frozen for the paper-facing experiments.

## Design

- 4 domains: HR, support, finance, enterprise documents
- 50 scenarios per domain
- 200 scenarios total
- 100 `full_registry` scenarios
- 100 `raw_only` scenarios
- 180 expected-allow scenarios
- 20 expected-deny purpose-conflict scenarios

Challenge families:

- `clean_natural`
- `semantic_ambiguity`
- `distractor_context`
- `raw_field_minimization`
- `purpose_conflict`
- `indirect_prompt_injection`
- `unseen_paraphrase`

For every model/repeat, one LLM proposal is generated per scenario and replayed
through both `llm_direct` and `llm_pbme`.

## Identifier and argument semantics

PBME treats identifiers as task-relative data. It does not mint, tokenize, or
replace enterprise identifiers.

- An identifier required by the signed task as a selector is preserved.
- An identifier required in verified returned data is preserved.
- An unrelated or unnecessary identifier is removed from the returned projection.
- An agent-supplied selector that is not bound to the trusted task is not allowed
  to silently change task scope.
- Necessity does not imply authorization.

`required_arguments` records trusted task-bound selectors/parameters.
`required_fields` records the minimum raw backend projection after selectors are
separated from returned data fields.

## Reproducibility compatibility

The public repository refers to this dataset simply as **E3**. The scenario IDs
retain the historical `E3V21-*` prefix and the internal split value remains
`frozen_eval_v2_1`. These strings are intentionally unchanged so previously
created validation traces and proposal cache keys remain reproducible. They do
not represent multiple active E3 benchmark versions in this repository.

## Generate

```bash
pbme-benchmark generate-e3
```

This writes:

```text
benchmark/e3/scenarios.jsonl
benchmark/e3/manifest.json
```

## Run

```bash
pbme-benchmark llm-run \
  --scenarios benchmark/e3/scenarios.jsonl \
  --variants all \
  --model gpt-6-luna \
  --repeats 1 \
  --out-dir benchmark/llm_results/validation_gpt6_luna_r1
```

The neutral prompt profile and exact prompt hash are stored in each run's
`run_config.json`.
