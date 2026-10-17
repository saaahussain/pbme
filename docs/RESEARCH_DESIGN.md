# Research Design

## Primary research question

Can a runtime governance layer reduce the information exposed to an AI agent
to the minimum required for a host-authorized task while preserving task
success?

## Hypotheses

- **H1:** Tool minimization reduces sensitive-data exposure beyond field
  projection alone.
- **H2:** Field minimization reduces unnecessary data access relative to
  permissive tool execution.
- **H3:** A planner-verifier split permits flexible task interpretation without
  allowing the planner to self-authorize.
- **H4:** Purpose enforcement blocks data that is task-relevant but unauthorized
  for the approved purpose.
- **H5:** The implemented `PBMEBroker` realizes the same policy decisions as
  the controlled simulator.

## Evaluation track E1 — policy simulation

E1 contains 500 deterministic scenarios across four domains and five variants.
Six policy configurations are each executed three times, producing 9,000
policy-simulation episodes.

The simulation deliberately isolates enforcement policy from model behavior.
It does not claim that an LLM independently selected the capability or tool.

### Baselines

1. Permissive execution
2. RBAC-only
3. Static response masking
4. ARES-like action-level allow/block guard
5. PBME field minimization
6. PBME full field + tool minimization

The ARES-like baseline is an abstraction of action-level resource mediation,
not a reproduction of the full ARES implementation.

## Evaluation track E2 — actual broker integration

E2 executes benchmark scenarios through the actual code path:

```text
TaskContextSigner
 -> PBMEBroker
 -> benchmark deterministic planner
 -> PlanVerifier
 -> GovernanceCatalog
 -> tool candidate scoring
 -> RequestRewriter
 -> DomainRuntime backend
 -> ResponseFilter
 -> JsonlAuditLog
```

Two modes are evaluated:

- **full_registry:** validates safe-tool selection/rerouting.
- **raw_only:** forces the request rewriter to project the verified minimum raw
  fields.

A backend over-return field is intentionally injected during E2 so response
filter correctness is directly observable.

## Evaluation track E3 — model behavior (future/optional)

A separate LLM-in-the-loop experiment can ask real models to select tools and
arguments. E3 should not be conflated with E1 or E2 because model planning
error and enforcement-policy error are different research questions.

## Metrics

### Task success rate

Percentage of episodes whose resulting answer/state matches deterministic
ground truth.

### Policy success / policy accuracy

Whether the system allows legitimate tasks and denies scenarios whose trusted
purpose is invalid.

### Exposure cost

Weighted cost of agent-visible fields based on sensitivity, PII status, and
direct-identification properties. It is an experimental comparative metric,
not a universal risk score.

### Unnecessary Data Access Rate (UDAR)

```text
unnecessary agent-visible fields / released agent-visible fields
```

For safe aggregate tools, necessity is evaluated against `safe_output_fields`.
For raw-record tools, it is evaluated against `required_fields`.

### Data Minimization Ratio (DMR)

```text
max(0, 1 - unique released fields / unique requested fields)
```

DMR is deliberately bounded at zero because a safer aggregate tool can return
a derived result field while still disclosing less sensitive information. Tool
substitution benefit is therefore evaluated primarily with exposure cost and
Tool Minimization Rate rather than field count alone.

### Tool Minimization Rate (TMR)

Percentage of episodes with a lower-exposure alternative in which the system
selects/reroutes to that safer tool.

### Attack Success Rate (ASR)

Percentage of adversarial-smuggling episodes in which a forbidden field reaches
the caller.

### False Denial Rate (FDR)

Percentage of legitimate scenarios denied by the evaluated policy.

### Broker agreement metrics

E2 additionally measures:

- simulator/broker policy agreement
- exact decision agreement
- selected-tool agreement
- released-field agreement
- field-rewrite accuracy
- response-filter accuracy
- audit completeness

### Latency

Decision/execution time measured by the harness. Synthetic in-process latency
must not be presented as production network/MCP latency.

## Experimental domains

- human resources
- customer support
- finance / expense analytics
- enterprise documents

All benchmark records are synthetic.

## Ablation

The central implemented ablation is:

```text
PBME-Field vs PBME-Full
```

This isolates the incremental value of safe-tool selection beyond field
projection. The reporting layer exports overall and domain/variant-specific
ablation tables.

Future ablations may include:

- no purpose binding
- no response filter
- semantic planner without deterministic verifier
- deterministic planner vs LLM planner

## Adversarial tests

Current benchmark coverage includes:

- over-broad / SELECT-*-equivalent field requests
- wrong approved purpose
- adversarial requests for all sensitive fields
- intentionally over-returning backends in broker validation
- signed-context tampering and expiry unit tests

Future E3 work should additionally cover indirect prompt injection, malicious
tool descriptions, cross-tool exfiltration, and model-generated field smuggling.
