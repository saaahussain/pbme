# Real Broker Validation

The original large benchmark is intentionally a policy simulator. This file
documents the second evaluation track that exercises the implemented
`PBMEBroker` end to end.

## Pipeline under test

```text
TaskContextSigner
  -> PBMEBroker
  -> BenchmarkInformationPlanner
  -> PlanVerifier
  -> GovernanceCatalog
  -> tool candidate scoring
  -> RequestRewriter
  -> DomainRuntime (SQLite)
  -> ResponseFilter
  -> JsonlAuditLog
```

The benchmark capability ontology is converted to ordinary core
`CapabilitySpec` objects. `PlanVerifier` and `PBMEBroker` now accept an
injectable trusted capability registry, so validation across HR, support,
finance, and documents uses the same broker implementation rather than a
separate domain-specific simulator.

## Trusted task parameters

`TaskContext` now carries signed `task_parameters`. This lets the trusted host
bind constraints such as year, customer ID, invoice ID, classification, or
department without trusting an agent-supplied argument to redefine task scope.

## Modes

### full_registry

Registers the raw-record tool plus every safe capability tool. This validates:

- purpose enforcement
- capability verification
- lowest-exposure tool selection
- rerouting
- output schema enforcement
- audit recording

### raw_only

Registers only the raw-record tool. Scenarios whose proposed tool is already a
safe aggregate tool are skipped. The broker must satisfy the task by rewriting
the raw call to the capability's verified `required_fields` projection.

This directly validates `RequestRewriter` instead of inferring field
minimization from the simulator.

## Response-filter fault injection

During validation, the selected backend executor intentionally appends one
undeclared field to each structured response. The field is known to the domain
catalog but is not in the broker-approved release schema.

A response-filter success occurs only when the actual caller-visible result no
longer contains the injected field.

## Deny auditing

Expected purpose denials are now emitted as structured `EnforcementRecord`
entries before `PBMEDenied` is raised. This allows audit completeness to be
measured for both allow/transform/reroute and deny outcomes.

## Reproduce

```bash
pbme-benchmark broker-run --repeats 3
```

See `benchmark/broker_results/broker_summary.json` and the CSV breakdowns for
the generated results.
