## Unreleased

- E3 harness now records completed-but-invalid LLM responses (for example, zero or multiple tool calls) as model proposal failures and continues the paired Direct/PBME run.
- Added invalid-proposal counts/rates and error-code breakdowns. Transport/API failures still fail loudly.
- Invalid proposals are cached during resume so failed model outputs are not selectively retried.

# Changelog

## Unreleased — OpenRouter E3 provider adapter

- Added `--provider openrouter` for E3 using the same frozen neutral prompt and tool schemas as the direct OpenAI path.
- Added `OPENROUTER_API_KEY` support through the OpenAI-compatible Chat Completions endpoint for broader cross-provider tool-calling compatibility.
- Added optional upstream-provider pinning, fallback disabling, and parameter-support routing controls for reproducible cross-model experiments.
- Added `--reasoning-effort omit` so non-OpenAI models can be tested without imposing an unsupported reasoning parameter.
- Added unit tests that verify frozen prompt parity, Chat Completions tool-schema conversion, exact-one-tool-call enforcement, provider routing payloads, OpenRouter authentication, base URL, and archived routing metadata.
- Added per-proposal OpenRouter upstream-provider/region capture and aggregate provider counts for auditable auto-routing.
- Added `.gitattributes` to keep the frozen E3 JSONL byte-stable (`eol=lf`) across Windows and Linux checkouts.

## 0.2.0 — Canonical E3 benchmark and real-LLM evaluation

- Added the canonical frozen 200-scenario E3 benchmark across HR, support, finance, and enterprise documents.
- Added paired `llm_direct` vs `llm_pbme` execution using the same real-LLM tool proposal in both conditions.
- Added the neutral prompt profile `neutral_tool_selection_v1` with prompt hashing in `run_config.json`.
- Separated signed task arguments/selectors from returned raw field projections.
- Preserved enterprise identifiers when required by the trusted task; PBME does not mint or replace enterprise IDs.
- Request rewriting drops unbound scope-changing arguments unless a tool explicitly permits agent passthrough.
- Added proposal metrics for over-broad fields, forbidden-field requests, unexpected arguments, and signed-argument mismatches.
- Added execution metrics for FFRR, reroute rate, and opportunity-conditioned TMR.
- Added scenario success separately from task completion so correct expected denials are not counted as completed user tasks.
- Added E3 per-variant and per-difficulty breakdowns, proposal caching/resume, token accounting, and CSV/JSONL artifacts.
- Consolidated active E3 source, tests, dataset paths, and CLI commands under the single public name `E3`.

## v0.1.0 — PBME public release

PBME (*Purpose-Bound Minimum-data Enforcement*) is the public research codebase.

Added in response to the evaluation/reviewer gap between policy simulation and
actual implementation validation:

- configurable capability registry in `DeterministicInformationPlanner`,
  `PlanVerifier`, and `PBMEBroker`
- signed `task_parameters` in `TaskContext`
- auditable deny decisions (`PBMEDenied.record`)
- explicit raw-record granularity penalty in tool optimization
- benchmark-to-broker adapter for all four domains
- `broker-run` validation CLI
- full-registry tool-minimization validation
- raw-only field-rewrite validation
- intentional backend over-return fault injection
- response-filter accuracy measurement
- simulator/broker policy, decision, tool, and field agreement metrics
- audit-completeness metric
- domain, variant, domain×variant reports
- PBME-Field vs PBME-Full ablation report
- `safe_output_fields` ground truth for correct UDAR measurement
- bounded DMR for aggregate-tool rerouting
- 19 automated tests
- regenerated 9,000-episode policy-simulation artifacts
- generated 2,700-episode real-broker integration artifacts

The large benchmark remains synthetic. No LLM-in-the-loop claims are made by
these artifacts.